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
    def dummy_print(self, *args, **kwargs):
        print("==== dummy_print: ")
        return (args[0],)

    return dummy_print


seq = paddle.nn.Sequential(paddle.nn.Linear(10, 1), paddle.nn.Linear(1, 2))
seq = nanofx.optimize(my_compiler)(seq)

x = paddle.rand([10, 10])
out = seq(x)

print(out)
