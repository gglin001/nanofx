from __future__ import annotations

import copy
import dis
import functools
import inspect
import itertools
import logging
import operator
import types

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from .bytecode_analysis import livevars_analysis
from .bytecode_transformation import (
    Instruction,
    cleaned_instructions,
    create_call_function,
    create_instruction,
    create_jump_absolute,
    transform_code_object,
    unique_id,
)
from .codegen import PyCodegen
from .output_graph import OutputGraph
from .source import LocalSource, Source
from .utils import log_code

if TYPE_CHECKING:
    # import opcode
    pass


_sym_var_id_counter = itertools.count()


class SymVar:
    def __init__(
        self,
        *,
        var: Any = None,
        vtype: Any = None,
        tx: PyEvalBase | None = None,
        source: Source | None = None,
    ) -> None:
        self.var = var
        self.vtype = vtype if var is None else type(var)
        self.tx = tx
        self.source = source

        self.id = f"id_{next(_sym_var_id_counter)}"

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"SymVar({self.vtype}, {self.id})"

    def call(self, tx: PyEvalBase, *args, **kwargs) -> Any:
        if inspect.isbuiltin(self.var):
            if self.var is print:
                raise NotImplementedError("print() is not supported")

        return tx.inline_call_function(self, args, kwargs)


def break_graph_if_unsupported(*, push: int):
    def decorator(inner_fn):
        @functools.wraps(inner_fn)
        def wrapper(self: PyEval, inst: Instruction):
            state = self.get_state()
            try:
                return inner_fn(self, inst)
            except NotImplementedError as excp:
                logging.debug(
                    f"break_graph_if_unsupported triggered compile", exc_info=True
                )

            self.set_state(state)

            # compile_subgraph
            self.output.compile_subgraph(self)

            # copy instruction, but without exception table data
            assert inst.target is None
            inst_copy = copy.copy(inst)
            inst_copy.exn_tab_entry = None
            self.output.add_output_instructions([inst_copy])

            stack_effect = dis.stack_effect(inst.opcode, inst.arg)
            self.popn(push - stack_effect)
            for _ in range(push):
                self.push(SymVar(var=None))

            self.output.add_output_instructions(
                self.create_call_resume_at(self.next_instruction)
            )

        return wrapper

    return decorator


class PyEvalState(NamedTuple):
    # output: OutputGraphState
    symbolic_locals: OrderedDict[str, Any]
    stack: list
    instruction_pointer: int
    current_instruction: Instruction | None
    next_instruction: Instruction | None
    lineno: int


class PyEvalBase:
    def __init__(
        self,
        *,
        instructions: list[Instruction],
        code_options: dict,
        f_code: types.CodeType,
        f_locals: dict[str, Any],
        f_globals: dict[str, Any],
        f_builtins: dict[str, Any],
        symbolic_locals: OrderedDict[str, SymVar],
        symbolic_globals: OrderedDict[str, Any],
        output: OutputGraph,
    ):
        self.instructions = instructions
        self.code_options = code_options
        self.symbolic_globals = symbolic_globals
        self.output = output

        self.f_code: types.CodeType = f_code
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.f_builtins = f_builtins
        self.should_exit = False

        # checkpoint
        self.checkpoint: tuple[Instruction, PyEvalState] | None = None
        self.symbolic_locals = symbolic_locals
        self.stack = []
        self.instruction_pointer = 0
        self.current_instruction: Instruction | None = None
        self.next_instruction: Instruction | None = None
        self.lineno = code_options["co_firstlineno"]

    def get_state(self):
        return PyEvalState(
            # self.output.get_state(),
            copy.copy(self.symbolic_locals),
            copy.copy(self.stack),
            self.instruction_pointer,
            self.current_instruction,
            self.next_instruction,
            self.lineno,
        )

    def set_state(self, state: PyEvalState):
        (
            # output_state,
            self.symbolic_locals,
            self.stack,
            self.instruction_pointer,
            self.current_instruction,
            self.next_instruction,
            self.lineno,
        ) = state

    def step(self):
        """Process exactly one instruction, return True if should exit."""
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
            logging.debug(f"TRACE starts_line {self.f_code.co_filename}:{self.lineno}")

        if len(self.stack) == 0:
            self.checkpoint = inst, self.get_state()

        logging.debug(f"TRACE {inst.opname} {inst.argval} {self.stack}")

        try:
            if not hasattr(self, inst.opname):
                raise NotImplementedError(f"missing: {inst.opname}")
            getattr(self, inst.opname)(inst)

            # return True if should exit
            return inst.opname == "RETURN_VALUE"
        except NotImplementedError as e:
            logging.debug(f"!! NotImplementedError: {e}")
        except Exception:
            raise

        # fallback
        logging.debug(f"graph break from {inst.opname} {inst.argval}")
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

    def run(self):
        while not self.should_exit and not self.output.should_exit and not self.step():
            pass

    def push(self, val: Any):
        self.stack.append(val)

    def pop(self) -> Any:
        return self.stack.pop()

    def popn(self, n: int) -> list[Any]:
        assert n >= 0
        return list(reversed([self.pop() for _ in range(n)]))

    def inline_call_function(
        self,
        fn: SymVar,
        args,
        kwargs,
    ):
        state = self.get_state()
        try:
            result = InlinePyEval.inline_call(self, fn, args, kwargs)
            return result
        except Exception:
            self.set_state(state)
            raise

    def call_function(
        self,
        fn: SymVar,
        args: list[SymVar],
        kwargs: dict[str, SymVar],
    ):
        var = fn.call(self, *args, **kwargs)

        self.push(SymVar(var=var))

    def prune_dead_locals(self):
        reads = livevars_analysis(self.instructions, self.current_instruction)
        self.symbolic_locals = OrderedDict(
            [(k, v) for k, v in self.symbolic_locals.items() if k in reads]
        )

    def POP_TOP(self, inst: Instruction):
        self.pop()

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

    def BINARY_ADD(self, inst: Instruction):
        fn = operator.add

        nargs = len(inspect.signature(fn).parameters)
        args = self.popn(nargs)
        assert type(args[0]) == type(args[1])
        self.push(SymVar(vtype=args[0].vtype))

    def BINARY_SUBTRACT(self, inst: Instruction):
        fn = operator.sub

        nargs = len(inspect.signature(fn).parameters)
        args = self.popn(nargs)
        assert type(args[0]) == type(args[1])
        self.push(SymVar(vtype=args[0].vtype))

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
    def RETURN_VALUE(self, inst: Instruction):
        self.should_exit = True
        self.prune_dead_locals()
        self.output.compile_subgraph(self)
        self.output.add_output_instructions([create_instruction("RETURN_VALUE")])

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
        self.push(SymVar(var=inst.argval))

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

    def JUMP_ABSOLUTE(self, inst: Instruction):
        for i, ins in enumerate(self.instructions):
            if inst.target.offset == ins.offset:
                self.instruction_pointer = i
                return
        raise Exception("JUMP_ABSOLUTE error")

    # def POP_JUMP_IF_FALSE(self, inst: Instruction):
    # def POP_JUMP_IF_TRUE(self, inst: Instruction):

    def LOAD_GLOBAL(self, inst: Instruction):
        name = inst.argval

        if name in self.f_globals:
            var = self.f_globals[name]
        elif name in self.f_builtins:
            var = self.f_builtins[name]
        else:
            raise Exception(f"name '{name}' is not found")

        self.push(SymVar(var=var))

    # def SETUP_FINALLY(self, inst: Instruction):
    def LOAD_FAST(self, inst: Instruction):
        name = inst.argval
        self.push(self.symbolic_locals[name])
        if name.startswith("___stack"):
            self.symbolic_locals.pop(name)

    def STORE_FAST(self, inst: Instruction):
        self.symbolic_locals[inst.argval] = self.pop()

    # def DELETE_FAST(self, inst: Instruction):

    # def RAISE_VARARGS(self, inst: Instruction):

    @break_graph_if_unsupported(push=1)
    def CALL_FUNCTION(self, inst: Instruction):
        # debug
        # raise NotImplementedError(f"error: {inst.opname}")
        args = self.popn(inst.argval)
        fn = self.pop()
        self.call_function(fn, args, {})

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
    def __init__(
        self,
        *,
        parent: PyEvalBase,
        code: types.CodeType,
        symbolic_locals: OrderedDict[str, Any],
        symbolic_globals: OrderedDict[str, Any],
        func: SymVar,
    ):
        f_globals = func.var.__globals__
        super().__init__(
            instructions=cleaned_instructions(code),
            code_options={k: getattr(code, k) for k in dir(code)},
            f_code=code,
            f_locals={},
            f_globals=f_globals,
            f_builtins=f_globals['__builtins__'],
            symbolic_locals=symbolic_locals,
            symbolic_globals=symbolic_globals,
            output=parent.output,
        )
        self.parent = parent
        self.symbolic_result = None
        # TODO
        # self.closure_cells = closure_cells

    @classmethod
    def inline_call(
        cls,
        parent: PyEvalBase,
        func: SymVar,
        args: list[SymVar],
        kwargs: dict[str, SymVar],
    ):
        code = func.var.__code__
        if code.co_name in ("__setitem__", "__setattr__"):
            raise NotImplementedError(f"inline_call {code.co_name}")

        logging.debug(f"INLINING {code}")
        log_code(code, "INLINE CODE")

        # TODO: bind_args()
        bound = inspect.signature(func.var).bind(*args, **kwargs)
        bound.apply_defaults()
        sub_locals = OrderedDict(bound.arguments.items())

        tracer = InlinePyEval(
            parent=parent,
            code=code,
            symbolic_locals=sub_locals,
            symbolic_globals=parent.symbolic_globals,
            func=func,
        )

        try:
            tracer.run()
        except Exception:
            logging.debug(f"FAILED INLINING {code}")
            raise
        assert tracer.symbolic_result is not None

        if tracer.f_globals is parent.f_globals:
            # Merge symbolic_globals back if parent and child are in the same namespace
            parent.symbolic_globals.update(tracer.symbolic_globals)

        logging.debug(f"DONE INLINING {code}")
        return tracer.symbolic_result

    def RETURN_VALUE(self, inst: Instruction):
        self.symbolic_result = self.pop()
        self.should_exit = True


class PyEval(PyEvalBase):
    def __init__(
        self,
        instructions: list[Instruction],
        frame: types.FrameType,
        code_options: dict,
        compiler_fn: Callable,
    ):
        super().__init__(
            instructions=instructions,
            f_code=frame.f_code,
            f_locals=frame.f_locals,
            f_globals=frame.f_globals,
            f_builtins=frame.f_builtins,
            code_options=code_options,
            symbolic_locals=OrderedDict(),
            symbolic_globals=OrderedDict(),
            output=OutputGraph(
                frame=frame,
                code_options=code_options,
                compiler_fn=compiler_fn,
                root_tx=self,
            ),
        )

        # TODO: support co_cellvars & co_freevars
        vars = list(code_options["co_varnames"])
        for k in vars:
            if k in frame.f_locals:
                self.symbolic_locals[k] = SymVar(
                    var=frame.f_locals[k],
                    source=LocalSource(k),
                )

        # init inputs
        for k in vars:
            if k in frame.f_locals:
                self.output.inputs.append(self.symbolic_locals[k])

    def create_call_resume_at(self, inst: Instruction | None) -> list[Instruction]:
        assert inst is not None
        self.instruction_pointer = -1

        if inst.opname == "RETURN_VALUE":
            return [create_instruction("RETURN_VALUE")]

        reads = livevars_analysis(self.instructions, inst)
        argnames = tuple(k for k in self.symbolic_locals.keys() if k in reads)

        cg = PyCodegen(self)

        stack_len = len(self.stack)
        nargs = stack_len + len(argnames)
        name = unique_id(f"__resume_at_{inst.offset}")

        # TODO: clean it
        # self.f_code
        # new_code: types.CodeType = ContinueExecutionCache.lookup(
        #     self.f_code,
        #     self.lineno,
        #     inst.offset,
        #     tuple(b.target.offset for b in self.block_stack),
        #     stack_len,
        #     argnames,
        #     tuple(b.resume_fn() for b in self.block_stack),
        #     tuple(null_idxes),
        # )
        # new_code = self.f_code

        def update(instructions: list[Instruction], code_options: dict):
            prefix = []
            code_options_update = {}

            args = [f"___stack{i}" for i in range(stack_len)]
            args.extend(v for v in argnames if v not in args)

            code_options_update["co_argcount"] = len(args)
            code_options_update["co_varnames"] = tuple(
                args + [v for v in code_options["co_varnames"] if v not in args]
            )

            nonlocal inst
            target = next(i for i in instructions if i.offset == inst.offset)

            for i in range(stack_len):
                prefix.append(create_instruction("LOAD_FAST", argval=f"___stack{i}"))
            prefix.append(create_jump_absolute(target))

            for inst in instructions:
                if inst.offset == target.offset:
                    break
                inst.starts_line = None

            code_options.update(code_options_update)
            instructions[:] = prefix + instructions

        new_code = transform_code_object(self.f_code, update)
        log_code(new_code, f"RESUME_AT {name}", log_fn=logging.debug)

        self.f_globals[name] = types.FunctionType(new_code, self.f_globals, name)

        cg.extend_output(cg.load_function_name(name, True, stack_len))

        cg.extend_output([cg.create_load(k) for k in argnames])
        cg.extend_output(create_call_function(nargs, False))
        cg.append_output(create_instruction("RETURN_VALUE"))
        return cg.instructions
