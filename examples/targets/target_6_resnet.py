from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)

import paddle
import paddle.nn

from paddle.vision.models import resnet18

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
        return (args[1],)

    return dummy_print


net = resnet18()
net.eval()
net = nanofx.optimize(my_compiler)(net)

example_input = paddle.rand([2, 3, 224, 224])
output = net(example_input)
print(output)
