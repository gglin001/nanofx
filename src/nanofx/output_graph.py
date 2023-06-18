from __future__ import annotations

import itertools
import logging
import types

from typing import TYPE_CHECKING, OrderedDict

from .bytecode_transformation import Instruction, create_instruction
from .codegen import PyCodegen
from .utils import log_instructions

if TYPE_CHECKING:
    from .ceval import PyEval, SymVar

_output_graph_var_counter = itertools.count()


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

    def add_output_instructions(self, insts: list[Instruction]) -> None:
        self.instructions.extend(insts)
        self.should_exit = True

    def apply_compiler(self, tx: PyEval):
        pass

    def compile_subgraph(self, tx: PyEval):
        stack_values = list(tx.stack)
        restore_vars = []
        val_to_names: OrderedDict[SymVar, list[str]] = OrderedDict()
        if stack_values:
            val_to_names[stack_values[-1]] = list()

        for k, v in tx.symbolic_locals.items():
            if v not in val_to_names:
                val_to_names[v] = list()
            val_to_names[v].append(k)
        for v in val_to_names.keys():
            restore_vars.extend(val_to_names[v])
            stack_values.extend([v] * len(val_to_names[v]))

        graph_output_var = f"____output_{next(_output_graph_var_counter)}"
        cg = PyCodegen(tx, graph_output_var)
        cg.call(stack_values)

        output = []
        # output.extend(self.apply_compiler(tx))

        if len(cg.graph_outputs) != 0:
            output.append(cg.create_store(graph_output_var))
        else:
            output.append(create_instruction("POP_TOP"))
        self.add_output_instructions(output + cg.instructions)

        self.add_output_instructions(
            [PyCodegen(tx).create_store(var) for var in reversed(restore_vars)]
        )

        logging.debug(f"compile_subgraph() self.instructions:")
        log_instructions(self.instructions)
