from __future__ import annotations

import itertools
import types

from typing import TYPE_CHECKING, Callable, OrderedDict

from .bytecode_transformation import Instruction, create_instruction
from .codegen import PyCodegen

if TYPE_CHECKING:
    from .pyeval import PyEval, PyEvalBase, SymVar

_output_graph_var_counter = itertools.count()

_compiled_fn_counter = itertools.count()


class Tracer:
    def __init__(self):
        pass


class OutputGraph:
    def __init__(
        self,
        frame: types.FrameType,
        code_options: dict,
        compiler_fn: Callable,
        root_tx: PyEval,
    ):
        self.instructions: list[Instruction] = []
        self.code_options = code_options
        self.compiler_fn = compiler_fn
        self.root_tx = root_tx

        self.inputs: list[SymVar] = []

        self.should_exit = False

    def add_output_instructions(self, insts: list[Instruction]) -> None:
        self.instructions.extend(insts)
        self.should_exit = True

    def apply_compiler(self, tx: PyEvalBase):
        from .eval_frame import disable

        compiled_fn_name = f"__compiled_fn_{next(_compiled_fn_counter)}"
        compiled_fn = self.compiler_fn(None, None)
        # log_code(compiled_fn.__code__, f"COMPILED_FN {compiled_fn_name}")
        compiled_fn = disable(compiled_fn)
        tx.f_globals[compiled_fn_name] = compiled_fn
        self.code_options['co_names'] += (compiled_fn_name,)

        cg = PyCodegen(tx)
        cg.make_call_generated_code(compiled_fn_name)
        return cg.instructions

    def compile_subgraph(self, tx: PyEvalBase):
        tx.prune_dead_locals()

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

        graph_output_var = f"___graph_out_{next(_output_graph_var_counter)}"
        self.code_options["co_varnames"] += (graph_output_var,)
        cg = PyCodegen(tx, graph_output_var)
        cg.call(stack_values)

        output = []
        output.extend(self.apply_compiler(tx))

        if len(cg.graph_outputs) != 0:
            output.append(cg.create_store(graph_output_var))
        else:
            output.append(create_instruction("POP_TOP"))
        self.add_output_instructions(output + cg.instructions)

        self.add_output_instructions(
            [PyCodegen(tx).create_store(var) for var in reversed(restore_vars)]
        )

        # log_instructions(self.instructions, 'compile_subgraph()')
