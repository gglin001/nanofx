from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)


import paddle
import paddle.nn

import nanofx

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def my_compiler(gl, example_inputs=None):
    print("my_compiler() called with FX graph:")

    gl.print_tabular()

    # dummy_print
    def dummy_print(*args, **kwargs):
        print("==== dummy_print: ")
        return (args[0],)

    return dummy_print


@nanofx.optimize(my_compiler)
def add(a, b):
    c = a + b
    c = a - b
    return c, a, b


in_a = paddle.ones([1], dtype='float32')
in_b = paddle.add(in_a, in_a)

res = add(in_a, in_b)

# print("in_a = ", in_a)
# print("in_b = ", in_b)
print("res = ", res)
