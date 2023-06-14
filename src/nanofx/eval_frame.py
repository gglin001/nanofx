from __future__ import annotations

import functools
import types

from ._eval_frame import set_eval_frame
from .convert_frame import convert_frame


class BaseContext:
    def __init__(self, callback):
        self.callback = callback

    def __enter__(self):
        self.old_callback = set_eval_frame(self.callback)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        set_eval_frame(self.old_callback)

    def __call__(self, fn):
        @functools.wraps(fn)
        def _fn(*args, **kwargs):
            old_callback = set_eval_frame(self.callback)

            result = fn(*args, **kwargs)
            set_eval_frame(old_callback)
            return result

        _fn.raw_fn = fn

        return _fn


class DisableContext(BaseContext):
    def __init__(self):
        super().__init__(callback=None)


def disable(fn=None):
    return DisableContext()(fn)


def optimize(backend: callable):
    def _fn(backend: callable):
        def __fn(frame: types.FrameType):
            result = convert_frame(frame, backend)
            return result

        return __fn

    return BaseContext(_fn(backend))
