from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)

import paddle
import paddle._C_ops
import paddle.nn

import nanofx

logging.basicConfig(level=logging.DEBUG, format="%(message)s")
# logging.basicConfig(level=logging.INFO, format="%(message)s")

paddle.seed(0)


def my_compiler(gl, example_inputs=None):
    print("my_compiler() called with FX graph:")

    gl.print_tabular()

    # gl.graph.print_tabular()
    # return gl.forward

    # dummy_print
    def dummy_print(*args, **kwargs):
        print("==== dummy_print: ")
        return (args[0],)

    return dummy_print


class M0(paddle.nn.Layer):
    def forward(self, input):
        out = paddle.add(input, input)
        return out


m0 = M0()


class MyLayer(paddle.nn.Layer):
    def __init__(self):
        super().__init__()
        self._linear = paddle.nn.Linear(1, 1)
        self._dropout = paddle.nn.Dropout(p=0.5)

    def forward(self, input):
        temp = self._linear(input)
        temp = self._dropout(temp)
        temp = m0(temp)
        return temp


mylayer = MyLayer()
mylayer.eval()

mylayer = nanofx.optimize(my_compiler)(mylayer)

x = paddle.randn([10, 1], 'float32')
out = mylayer(x)
print("res = ", out)
