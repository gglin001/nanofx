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

        # fallback
        assert not self.output.instructions
        assert self.checkpoint is not None
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

    # def POP_TOP(self, inst: Instruction):
    # def ROT_TWO(self, inst: Instruction):
    # def ROT_THREE(self, inst: Instruction):
    # def DUP_TOP(self, inst: Instruction):
    # def DUP_TOP_TWO(self, inst: Instruction):
    # def ROT_FOUR(self, inst: Instruction):

    # def NOP(self, inst: Instruction):
    # def UNARY_POSITIVE(self, inst: Instruction):
    # def UNARY_NEGATIVE(self, inst: Instruction):
    # def UNARY_NOT(self, inst: Instruction):

    # def UNARY_INVERT(self, inst: Instruction):

    # def BINARY_MATRIX_MULTIPLY(self, inst: Instruction):
    # def INPLACE_MATRIX_MULTIPLY(self, inst: Instruction):

    # def BINARY_POWER(self, inst: Instruction):
    # def BINARY_MULTIPLY(self, inst: Instruction):

    # def BINARY_MODULO(self, inst: Instruction):
    # def BINARY_ADD(self, inst: Instruction):
    # def BINARY_SUBTRACT(self, inst: Instruction):
    # def BINARY_SUBSCR(self, inst: Instruction):
    # def BINARY_FLOOR_DIVIDE(self, inst: Instruction):
    # def BINARY_TRUE_DIVIDE(self, inst: Instruction):
    # def INPLACE_FLOOR_DIVIDE(self, inst: Instruction):
    # def INPLACE_TRUE_DIVIDE(self, inst: Instruction):

    # def GET_AITER(self, inst: Instruction):
    # def GET_ANEXT(self, inst: Instruction):
    # def BEFORE_ASYNC_WITH(self, inst: Instruction):
    # def BEGIN_FINALLY(self, inst: Instruction):
    # def END_ASYNC_FOR(self, inst: Instruction):
    # def INPLACE_ADD(self, inst: Instruction):
    # def INPLACE_SUBTRACT(self, inst: Instruction):
    # def INPLACE_MULTIPLY(self, inst: Instruction):

    # def INPLACE_MODULO(self, inst: Instruction):
    # def STORE_SUBSCR(self, inst: Instruction):
    # def DELETE_SUBSCR(self, inst: Instruction):
    # def BINARY_LSHIFT(self, inst: Instruction):
    # def BINARY_RSHIFT(self, inst: Instruction):
    # def BINARY_AND(self, inst: Instruction):
    # def BINARY_XOR(self, inst: Instruction):
    # def BINARY_OR(self, inst: Instruction):
    # def INPLACE_POWER(self, inst: Instruction):
    # def GET_ITER(self, inst: Instruction):
    # def GET_YIELD_FROM_ITER(self, inst: Instruction):

    # def PRINT_EXPR(self, inst: Instruction):
    # def LOAD_BUILD_CLASS(self, inst: Instruction):
    # def YIELD_FROM(self, inst: Instruction):
    # def GET_AWAITABLE(self, inst: Instruction):

    # def INPLACE_LSHIFT(self, inst: Instruction):
    # def INPLACE_RSHIFT(self, inst: Instruction):
    # def INPLACE_AND(self, inst: Instruction):
    # def INPLACE_XOR(self, inst: Instruction):
    # def INPLACE_OR(self, inst: Instruction):
    # def WITH_CLEANUP_START(self, inst: Instruction):
    # def WITH_CLEANUP_FINISH(self, inst: Instruction):
    # def RETURN_VALUE(self, inst: Instruction):
    # def IMPORT_STAR(self, inst: Instruction):
    # def SETUP_ANNOTATIONS(self, inst: Instruction):
    # def YIELD_VALUE(self, inst: Instruction):
    # def POP_BLOCK(self, inst: Instruction):
    # def END_FINALLY(self, inst: Instruction):
    # def POP_EXCEPT(self, inst: Instruction):

    # def STORE_NAME(self, inst: Instruction):
    # def DELETE_NAME(self, inst: Instruction):
    # def UNPACK_SEQUENCE(self, inst: Instruction):
    # def FOR_ITER(self, inst: Instruction):
    # def UNPACK_EX(self, inst: Instruction):
    # def STORE_ATTR(self, inst: Instruction):
    # def DELETE_ATTR(self, inst: Instruction):
    # def STORE_GLOBAL(self, inst: Instruction):
    # def DELETE_GLOBAL(self, inst: Instruction):
    def LOAD_CONST(self, inst: Instruction):
        pass

    # def LOAD_NAME(self, inst: Instruction):
    # def BUILD_TUPLE(self, inst: Instruction):
    # def BUILD_LIST(self, inst: Instruction):
    # def BUILD_SET(self, inst: Instruction):
    # def BUILD_MAP(self, inst: Instruction):
    # def LOAD_ATTR(self, inst: Instruction):
    # def COMPARE_OP(self, inst: Instruction):

    # def IMPORT_NAME(self, inst: Instruction):
    # def IMPORT_FROM(self, inst: Instruction):

    # def JUMP_FORWARD(self, inst: Instruction):
    # def JUMP_IF_FALSE_OR_POP(self, inst: Instruction):
    # def JUMP_IF_TRUE_OR_POP(self, inst: Instruction):
    # def JUMP_ABSOLUTE(self, inst: Instruction):
    # def POP_JUMP_IF_FALSE(self, inst: Instruction):
    # def POP_JUMP_IF_TRUE(self, inst: Instruction):

    # def LOAD_GLOBAL(self, inst: Instruction):
    # def SETUP_FINALLY(self, inst: Instruction):
    # def LOAD_FAST(self, inst: Instruction):
    # def STORE_FAST(self, inst: Instruction):
    # def DELETE_FAST(self, inst: Instruction):

    # def RAISE_VARARGS(self, inst: Instruction):
    # def CALL_FUNCTION(self, inst: Instruction):
    # def MAKE_FUNCTION(self, inst: Instruction):
    # def BUILD_SLICE(self, inst: Instruction):
    # def LOAD_CLOSURE(self, inst: Instruction):
    # def LOAD_DEREF(self, inst: Instruction):
    # def STORE_DEREF(self, inst: Instruction):
    # def DELETE_DEREF(self, inst: Instruction):

    # def CALL_FUNCTION_KW(self, inst: Instruction):
    # def CALL_FUNCTION_EX(self, inst: Instruction):

    # def SETUP_WITH(self, inst: Instruction):

    # def LIST_APPEND(self, inst: Instruction):
    # def SET_ADD(self, inst: Instruction):
    # def MAP_ADD(self, inst: Instruction):
    # def LOAD_CLASSDEREF(self, inst: Instruction):
    # def EXTENDED_ARG(self, inst: Instruction):
    # def BUILD_LIST_UNPACK(self, inst: Instruction):
    # def BUILD_MAP_UNPACK(self, inst: Instruction):
    # def BUILD_MAP_UNPACK_WITH_CALL(self, inst: Instruction):
    # def BUILD_TUPLE_UNPACK(self, inst: Instruction):
    # def BUILD_SET_UNPACK(self, inst: Instruction):

    # def SETUP_ASYNC_WITH(self, inst: Instruction):

    # def FORMAT_VALUE(self, inst: Instruction):
    # def BUILD_CONST_KEY_MAP(self, inst: Instruction):
    # def BUILD_STRING(self, inst: Instruction):
    # def BUILD_TUPLE_UNPACK_WITH_CALL(self, inst: Instruction):
    # def LOAD_METHOD(self, inst: Instruction):
    # def CALL_METHOD(self, inst: Instruction):
    # def CALL_FINALLY(self, inst: Instruction):
    def POP_FINALLY(self, inst: Instruction):
        raise NotImplementedError(f"missing: {inst.opname}")


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
