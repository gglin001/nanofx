from __future__ import annotations

import types

from typing import TYPE_CHECKING

from .bytecode_transformation import Instruction
from .codegen import PyCodegen
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


class InlinePyEval(PyEvalBase):
    pass


class PyEval(PyEvalBase):
    def __init__(
        self,
        instructions: list[Instruction],
        frame: types.FrameType,
        code_options: dict,
        compiler_fn: callable,
    ):
        super().__init__(
            instructions,
            frame,
            compiler_fn,
            OutputGraph(
                frame=frame,
                code_options=code_options,
                compiler_fn=compiler_fn,
                root_tx=self,
            ),
        )

    def run(self):
        from .eval_frame import disable

        compiled_fn = self.compiler_fn(None, None)
        compiled_fn = disable(compiled_fn)

        compiled_fn_name = f"__compiled_fn_{0}"
        self.frame.f_globals[compiled_fn_name] = compiled_fn
        self.output.code_options['co_names'] += (compiled_fn_name,)

        cg = PyCodegen()
        cg.make_call_generated_code(compiled_fn_name)

        self.output.instructions.extend(cg.get_instructions())
        self.output.instructions.append(cg.create_load_const(None))
        self.output.instructions.append(cg.create_instruction("RETURN_VALUE"))
