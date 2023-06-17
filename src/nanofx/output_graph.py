from __future__ import annotations

import types

from typing import TYPE_CHECKING

from .bytecode_transformation import Instruction

if TYPE_CHECKING:
    from .ceval import PyEval


class OutputGraph:
    def __init__(
        self,
        frame: types.FrameType,
        code_options: dict,
        compiler_fn: callable,
        root_tx: PyEval,
    ):
        self.instructions: list[Instruction] = []
        self.code_options = code_options
        self.compiler_fn = compiler_fn
        self.root_tx = root_tx

        self.should_exit = False

    def compile_subgraph(self, tx: PyEval):
        # TODO
        raise NotImplementedError(f"Notimplemented compile_subgraph() ")

    def add_output_instructions(self, insts: list[Instruction]) -> None:
        self.instructions.extend(insts)
        self.should_exit = True
