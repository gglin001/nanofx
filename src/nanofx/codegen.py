from __future__ import annotations

import collections
import sys

from functools import lru_cache
from typing import TYPE_CHECKING

from .bytecode_transformation import *  # noqa
from .paddle_utils import TensorType

if TYPE_CHECKING:
    from .ceval import SymVar


@lru_cache(32)
def rot_n_helper(n):
    assert n > 1
    vars = [f"v{i}" for i in range(n)]
    rotated = reversed(vars[-1:] + vars[:-1])
    fn = eval(f"lambda {','.join(vars)}: ({','.join(rotated)})")
    fn.__name__ = f"rot_{n}_helper"
    return fn


class PyCodegen:
    def __init__(
        self,
        tx=None,
        graph_output_var: str = None,
    ):
        self.tx = tx
        self.code_options = self.tx.output.code_options

        self.graph_output_var = graph_output_var

        self.top_of_stack = None
        self.graph_outputs = collections.OrderedDict()
        self.instructions: list[Instruction] = []

    def call_one(self, value: SymVar):
        """Generate code such that top-of-stack (TOS) is set to value."""
        output = self.instructions
        graph_outputs = self.graph_outputs

        if self.top_of_stack is value:
            output.append(create_dup_top())
            return

        if isinstance(value.vtype, (TensorType,)):
            graph_outputs_key = id(value)
            if graph_outputs_key not in graph_outputs:
                graph_outputs[graph_outputs_key] = value

            output.append(self.create_load(self.graph_output_var))
            # TODO: rm hardcode
            output.append(self.create_load_const(0))
            output.append(create_instruction("BINARY_SUBSCR"))
        else:
            # TODO: support container types
            raise NotImplementedError(f"unsupported type: {type(value)}")

        self.top_of_stack = value

    def call(self, vars: list[SymVar]):
        for var in vars:
            self.call_one(var)

    def clear_tos(self):
        self.top_of_stack = None

    def append_output(self, inst):
        assert isinstance(inst, Instruction)
        self.instructions.append(inst)
        self.clear_tos()

    def extend_output(self, insts):
        assert all(isinstance(x, Instruction) for x in insts)
        self.instructions.extend(insts)
        self.clear_tos()

    def create_load(self, name):
        # assert name in self.code_options["co_varnames"], f"{name} missing"
        return create_instruction("LOAD_FAST", argval=name)

    def create_store(self, name):
        # assert name in self.code_options["co_varnames"]
        return create_instruction("STORE_FAST", argval=name)

    def create_load_global(self, name, push_null):
        assert name in self.code_options["co_names"], f"{name} not in co_names"
        return create_load_global(name, push_null)

    def create_load_const(self, value):
        return create_instruction("LOAD_CONST", argval=value)

    def create_load_attr(self, name):
        if name not in self.code_options["co_names"]:
            self.code_options["co_names"] += (name,)
        return create_instruction("LOAD_ATTR", argval=name)

    def create_load_attrs(self, names):
        return [self.create_load_attr(name) for name in names.split(".")]

    def load_function_name(self, fn_name, push_null, num_on_stack=0):
        """Load the global fn_name on the stack num_on_stack down."""
        output = []
        output.extend(
            [
                self.create_load_global(fn_name, False, add=True),
                *self.rot_n(num_on_stack + 1),
            ]
        )
        return output

    def rot_n(self, n):
        try:
            return create_rot_n(n)
        except AttributeError:
            # desired rotate bytecode doesn't exist, generate equivalent bytecode
            return [
                create_instruction("BUILD_TUPLE", arg=n),
                self.create_load_output(rot_n_helper(n)),
                *create_rot_n(2),
                create_instruction("CALL_FUNCTION_EX", arg=0),
                create_instruction("UNPACK_SEQUENCE", arg=n),
            ]

    def create_call_function_kw(self, nargs, kw_names, push_null):
        if sys.version_info >= (3, 11):
            output = create_call_function(nargs, push_null)
            assert output[-2].opname == "PRECALL"
            kw_names_inst = create_instruction("KW_NAMES", argval=kw_names)
            output.insert(-2, kw_names_inst)
            return output
        return [
            self.create_load_const(kw_names),
            create_instruction("CALL_FUNCTION_KW", arg=nargs),
        ]

    def make_call_generated_code(self, fn_name: str):
        load_function = create_load_global(fn_name, False)
        self.extend_output([load_function])

        # placeholders = self.tx.output.placeholders
        # for x in placeholders:
        #     load_fast = create_instruction(
        #         "LOAD_FAST",
        #         argval=x.name,
        #     )
        #     self.extend_output([load_fast])

        call_function = create_instruction(
            "CALL_FUNCTION",
            # arg=len(placeholders),
            arg=0,
        )
        self.extend_output([call_function])
