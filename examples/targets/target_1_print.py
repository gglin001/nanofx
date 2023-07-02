from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)


import paddle
import paddle.nn

import nanofx

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def my_compiler(gl: nanofx.GraphLayer, example_inputs: list[paddle.Tensor] = None):
    print("my_compiler() called with FX graph:")

    # gl.graph.print_tabular()
    # return gl.forward

    # dummy_print
    def dummy_print(*args, **kwargs):
        print("\n==== dummy_print: ")
        for arg in args:
            print(arg)
        print("==== fin dummy_print\n")
        # return arg

    return dummy_print


@nanofx.optimize(my_compiler)
def func(x, y):
    z = x + y
    print("zzzz")
    # a = z - z
    zz = x - y
    return zz


in_a = paddle.rand([1])
in_b = paddle.rand([1])

res = func(in_a, in_b)

# print("in_a = ", in_a)
# print("in_b = ", in_b)
print("res = ", res)
