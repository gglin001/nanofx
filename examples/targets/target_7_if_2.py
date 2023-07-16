from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)


import paddle
import paddle.nn

import nanofx
import nanofx.utils

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


def if_func(x, z):
    if x:
        return x + x
    return z + z


@nanofx.optimize(my_compiler)
def add(x, y):
    z = x + y
    res = if_func(x, z)
    return res


in_a = paddle.rand([1])
in_b = paddle.rand([1])
res = add(in_a, in_b)

# print("in_a = ", in_a)
# print("in_b = ", in_b)
print("res = ", res)
