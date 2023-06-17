from __future__ import annotations

import dataclasses
import types

from typing import Any

from .bytecode_transformation import Instruction, transform_code_object
from .ceval import PyEval
from .paddle_utils import Tensor, skip_paddle_frame
from .utils import print_bytecode, print_code


@dataclasses.dataclass
class GuardedCode:
    code: types.CodeType


def skip_frame(frame: types.FrameType) -> bool:
    if skip_paddle_frame(frame):
        return True

    for v in frame.f_locals.values():
        if isinstance(v, Tensor):
            return False

    return True


def convert_frame(frame: types.FrameType, compiler_fn: callable) -> Any:
    if skip_frame(frame):
        return None

    def transform(instructions: list[Instruction], code_options: dict):
        tracer = PyEval(instructions, frame, code_options, compiler_fn)
        tracer.run()

        code_options.update(tracer.output.code_options)
        instructions[:] = tracer.output.instructions

    print(f"convert_frame: {frame}")
    code = frame.f_code

    # TODO: rm torch code dependency
    out_code = transform_code_object(code, transform)

    print_code(code, "RAW BYTECODE")
    print_bytecode(
        "NEW BYTECODE", code.co_name, code.co_filename, code.co_firstlineno, out_code
    )

    # debug, no trace
    # return None

    g = GuardedCode(out_code)
    return g
