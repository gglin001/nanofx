from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)

import paddle

import nanofx

logging.basicConfig(level=logging.DEBUG, format="%(message)s")
# logging.basicConfig(level=logging.INFO, format="%(message)s")


def my_compiler(gl: nanofx.GraphLayer, example_inputs: list[paddle.Tensor] = None):
    print("my_compiler() called with FX graph:")

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
    e = paddle.add(c, d)
    return e


in_a = paddle.rand([1])
in_b = paddle.rand([1])
res = net(in_a, in_b)
print("res = ", res)
