from __future__ import annotations

import types

from typing import TYPE_CHECKING

from .bytecode_transformation import Instruction
from .output_graph import OutputGraph

if TYPE_CHECKING:
    pass


class PyEvalBase:
    def __init__(
        self,
        instructions: list[Instruction],
        frame: types.FrameType,
        compiler_fn: callable,
        output: OutputGraph,
    ):
        self.instructions = instructions
        self.frame = frame
        self.compiler_fn = compiler_fn
        self.output = output


class PyEval(PyEvalBase):
    def __init__(
        self,
        instructions: list[Instruction],
        frame: types.FrameType,
        compiler_fn: callable,
    ):
        super().__init__(
            instructions,
            frame,
            compiler_fn,
            OutputGraph(frame=frame, compiler_fn=compiler_fn, root_tx=self),
        )


class InlinePyEval(PyEvalBase):
    pass
