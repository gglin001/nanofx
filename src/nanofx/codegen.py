from __future__ import annotations

import collections
import sys

from typing import TYPE_CHECKING

from .bytecode_transformation import *  # noqa

if TYPE_CHECKING:
    pass


class PyCodegen:
    def __init__(
        self,
        tx=None,
        graph_output_var: str = None,
    ):
        self.graph_output_var = graph_output_var

        self.tx = tx
        # self.code_options = self.tx.output.code_options
        # self.cell_and_freevars = self.tx.cell_and_freevars
        # self.new_var = self.tx.output.new_var

        self.top_of_stack = None
        self.graph_outputs = collections.OrderedDict()
        self._output: list[Instruction] = []

    def graph_output_vars(self):
        return [x.variable for x in self.graph_outputs.values()]

    def __call__(self, value):
        """Generate code such that top-of-stack (TOS) is set to value."""

        if isinstance(value, Source):
            self._output.extend(value.reconstruct(self))
            self.clear_tos()
            return

        assert isinstance(value, VariableTracker)
        output = self._output
        graph_outputs = self.graph_outputs

        if self.top_of_stack is value:
            output.append(create_dup_top())
            return

        if value.is_python_constant() and is_safe_constant(value.as_python_constant()):
            output.append(self.create_load_const(value.as_python_constant()))
        elif isinstance(
            value,
            (
                TensorVariable,
                SymNodeVariable,
                TensorWithTFOverrideVariable,
                UnspecializedPythonVariable,
                NumpyNdarrayVariable,
            ),
        ):
            if isinstance(value, TensorWithTFOverrideVariable):
                # unwrap back to tensor
                value = value.tensor_variable
            graph_outputs_key = id(value.proxy)
            if graph_outputs_key not in graph_outputs:
                graph_outputs[graph_outputs_key] = GraphOutputEntry(
                    len(graph_outputs), value
                )
            else:
                graph_outputs[graph_outputs_key].merge(value)
            if isinstance(value, NumpyNdarrayVariable):
                self.load_import_from(utils.__name__, "to_numpy_helper")
            output.append(self.create_load(self.graph_output_var))
            output.append(
                self._create_load_const(graph_outputs[graph_outputs_key].index)
            )
            output.append(create_instruction("BINARY_SUBSCR"))
            if isinstance(value, NumpyNdarrayVariable):
                output.extend(create_call_function(1, False))
            elif isinstance(value, UnspecializedPythonVariable) and value.need_unwrap:
                output.extend(
                    [self.create_load_attr("item")] + create_call_function(0, True)
                )
        else:
            try:
                output.extend(value.reconstruct(self))
            except NotImplementedError:
                unimplemented(f"reconstruct: {value}")

        self.top_of_stack = value

    def foreach(self, items):
        for i in items:
            self(i)

    def clear_tos(self):
        self.top_of_stack = None

    def append_output(self, inst):
        assert isinstance(inst, Instruction)
        self._output.append(inst)
        self.clear_tos()

    def extend_output(self, insts):
        assert all(isinstance(x, Instruction) for x in insts)
        self._output.extend(insts)
        self.clear_tos()

    def get_instructions(self):
        return self._output

    def create_load(self, name):
        assert name in self.code_options["co_varnames"], f"{name} missing"
        return create_instruction("LOAD_FAST", argval=name)

    def create_store(self, name):
        assert name in self.code_options["co_varnames"]
        return create_instruction("STORE_FAST", argval=name)

    def create_load_global(self, name, push_null):
        assert name in self.code_options["co_names"], f"{name} not in co_names"
        return create_load_global(name, push_null)

    def create_load_const(self, value):
        return self._create_load_const(value)

    def _create_load_const(self, value):
        return create_instruction("LOAD_CONST", argval=value)

    create_load_output = _create_load_const

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
                self._create_load_const(rot_n_helper(n)),
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

    def create_instruction(self, opname, arg=None, argval=None):
        return create_instruction(opname, arg=arg, argval=argval)