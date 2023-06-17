from __future__ import annotations

import types

from typing import TYPE_CHECKING, NamedTuple

from .bytecode_transformation import Instruction, create_jump_absolute
from .output_graph import OutputGraph

if TYPE_CHECKING:
    pass


class PyEvalState(NamedTuple):
    # output: OutputGraphState
    # symbolic_locals: Dict[str, VariableTracker]
    stack: list
    instruction_pointer: int
    current_instruction: Instruction | None
    next_instruction: Instruction | None
    lineno: int


class PyEvalBase:
    def __init__(
        self,
        instructions: list[Instruction],
        frame: types.FrameType,
        code_options: dict,
        compiler_fn: callable,
        output: OutputGraph,
    ):
        self.instructions = instructions
        self.frame = frame
        self.compiler_fn = compiler_fn
        self.output = output
        self.code_options = code_options

        self.f_code: types.CodeType = frame.f_code
        self.should_exit = False

        # checkpoint status
        self.checkpoint: tuple[Instruction, PyEvalState] | None = None
        self.stack = []
        self.instruction_pointer = 0
        self.current_instruction: Instruction = None
        self.next_instruction: Instruction = None
        self.lineno = code_options["co_firstlineno"]

    def get_state(self):
        return PyEvalState(
            # self.output.copy_graphstate(),
            # collections.OrderedDict(self.symbolic_locals),
            self.stack,
            self.instruction_pointer,
            self.current_instruction,
            self.next_instruction,
            self.lineno,
        )

    def set_state(self, state: PyEvalState):
        (
            # output_state,
            # self.symbolic_locals,
            self.stack,
            self.instruction_pointer,
            self.current_instruction,
            self.next_instruction,
            self.lineno,
        ) = state

    def step(self):
        """Process exactly one instruction, return True if should exit."""
        assert isinstance(self.instruction_pointer, int)
        inst = self.instructions[self.instruction_pointer]
        self.current_instruction = inst
        self.instruction_pointer += 1
        if self.instruction_pointer < len(self.instructions):
            self.next_instruction = self.instructions[self.instruction_pointer]
        else:
            self.should_exit = True
            self.next_instruction = None
        if inst.starts_line and self.lineno != inst.starts_line:
            self.lineno = inst.starts_line
            print(f"TRACE starts_line %s:%s", self.f_code.co_filename, self.lineno)

        if len(self.stack) == 0:
            self.checkpoint = inst, self.get_state()

        print("TRACE %s %s %s", inst.opname, inst.argval, self.stack)

        try:
            if not hasattr(self, inst.opname):
                raise NotImplementedError(f"missing: {inst.opname}")
            getattr(self, inst.opname)(inst)

            # return True if should exit
            # return inst.opname == "RETURN_VALUE"
            if inst.opname == "RETURN_VALUE":
                return True
        except NotImplementedError as e:
            print(f"NotImplementedError raised")
        except Exception as e:
            raise e

        # generate code from checkpoint
        # assert not self.output.output_instructions
        # assert self.checkpoint is not None

        continue_inst, state = self.checkpoint
        self.set_state(state)
        self.output.compile_subgraph(self)
        self.output.add_output_instructions(
            [create_jump_absolute(continue_inst)] + self.instructions
        )

        self.should_exit = True
        return True

        # from .eval_frame import disable
        # compiled_fn = self.compiler_fn(None, None)
        # compiled_fn = disable(compiled_fn)
        # compiled_fn_name = f"__compiled_fn_{0}"
        # self.frame.f_globals[compiled_fn_name] = compiled_fn
        # self.output.code_options['co_names'] += (compiled_fn_name,)
        # cg = PyCodegen()
        # cg.make_call_generated_code(compiled_fn_name)
        # self.output.instructions.extend(cg.get_instructions())
        # self.output.instructions.append(cg.create_load_const(None))
        # self.output.instructions.append(cg.create_instruction("RETURN_VALUE"))

    def run(self):
        while not self.should_exit and not self.output.should_exit:
            if self.step():
                return


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
            code_options,
            compiler_fn,
            OutputGraph(
                frame=frame,
                code_options=code_options,
                compiler_fn=compiler_fn,
                root_tx=self,
            ),
        )
