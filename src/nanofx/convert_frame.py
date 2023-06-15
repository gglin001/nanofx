from __future__ import annotations

import dataclasses
import types

from typing import Any, Callable

from .bytecode_transformation import transform_code_object
from .codegen import PyCodegen
from .utils import print_bytecode, print_code


@dataclasses.dataclass
class GuardedCode:
    code: types.CodeType


def skip_frame(frame: types.FrameType) -> bool:
    import paddle

    # NOTE: skip paddle internal code
    if frame.f_code.co_filename.endswith('paddle/fluid/dygraph/math_op_patch.py'):
        return True
    elif frame.f_code.co_filename.endswith('paddle/fluid/framework.py'):
        return True
    elif frame.f_code.co_name == 'in_dygraph_mode':
        return True

    for v in frame.f_locals.values():
        if isinstance(v, paddle.Tensor):
            return False

    return True


def convert_frame(frame: types.FrameType, compiler: Callable) -> Any:
    from .eval_frame import disable

    if skip_frame(frame):
        return None

    print(f"convert_frame: {frame}")
    code = frame.f_code

    compiled_fn = compiler(code, None)
    compiled_fn = disable(compiled_fn)

    compiled_fn_name = f"__compiled_fn_{0}"
    frame.f_globals[compiled_fn_name] = compiled_fn

    def transform(instructions, code_options):
        code_options['co_names'] += (compiled_fn_name,)

        out_instructions = []
        cg = PyCodegen()
        cg.make_call_generated_code(compiled_fn_name)

        out_instructions.extend(cg.get_instructions())
        out_instructions.append(cg.create_load_const(None))
        out_instructions.append(cg.create_instruction("RETURN_VALUE"))

        instructions[:] = out_instructions

    out_code = transform_code_object(code, transform)

    print_code(code, "RAW BYTECODE")
    print_bytecode(
        "NEW BYTECODE", code.co_name, code.co_filename, code.co_firstlineno, out_code
    )

    # debug, no trace
    # return None

    g = GuardedCode(out_code)
    return g
