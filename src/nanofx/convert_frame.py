from __future__ import annotations

import dis
import logging
import types

from typing import Any, Callable


def has_tensor_in_frame(frame: types.FrameType) -> bool:
    import paddle

    # NOTE: skip paddle internal code
    if frame.f_code.co_filename.endswith('paddle/fluid/dygraph/math_op_patch.py'):
        return False
    if frame.f_code.co_name == 'in_dygraph_mode':
        return False

    for v in frame.f_locals.values():
        if isinstance(v, paddle.Tensor):
            return True

    return False


def convert_frame(frame: types.FrameType, compiler_fn: Callable) -> Any:
    f_code = frame.f_code

    logging.debug(f"\nraw_code:")
    [logging.debug(x) for x in list(dis.get_instructions(f_code))]
    logging.debug(f"")

    # debug, no trace
    return None

    # g = GuardedCode(out_code)
    # return g
