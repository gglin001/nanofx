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


def my_compiler(gl, example_inputs=None):
    print("my_compiler() called with FX graph:")

    # gl.graph.print_tabular()
    # return gl.forward

    # dummy_print
    def dummy_print(*args, **kwargs):
        print("==== dummy_print: ")
        return (args[0],)

    return dummy_print


def func1(a0, b0):
    c = a0 + b0
    return c


def func0(a, b):
    c = func1(a, b)
    return c


@nanofx.optimize(my_compiler)
def add(x, y):
    z = func0(x, y)
    return z


in_a = paddle.ones([1], dtype='float32')
in_b = paddle.add(in_a, in_a)
res = add(in_a, in_b)

# print("in_a = ", in_a)
# print("in_b = ", in_b)
print("res = ", res)
