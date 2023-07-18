from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)

import paddle
import paddle._C_ops

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


@nanofx.optimize(my_compiler)
def net(a, b):
    c = paddle.add(a, b)
    d = paddle.multiply(c, a)
    e = paddle._C_ops.add(a, b)
    return e


in_a = paddle.ones([1], dtype='float32')
in_b = paddle.add(in_a, in_a)
res = net(in_a, in_b)
print("res = ", res)
