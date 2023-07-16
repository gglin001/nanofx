from __future__ import annotations

import logging

# ignore DeprecationWarning from `pkg_resources`
logging.captureWarnings(True)

import paddle
import paddle.nn

from paddle.vision.models import resnet18

net = resnet18()

example_input = paddle.rand([2, 3, 224, 224])
orig_output = net(example_input)
print(orig_output)
