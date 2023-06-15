from __future__ import annotations

import dataclasses
import types

from typing import Any, Callable

from .utils import print_bytecode


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
    frame.f_globals['__compiled_fn_0'] = compiled_fn

    # TODO: add CALL_FUNCTION to compiled_fn
    out_code = compiled_fn.__code__
    # out_code = []

    print_bytecode(code, "RAW BYTECODE")
    print_bytecode(
        "NEW BYTECODE", code.co_name, code.co_filename, code.co_firstlineno, out_code
    )

    # debug, no trace
    return None

    g = GuardedCode(out_code)
    return g
