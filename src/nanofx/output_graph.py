from __future__ import annotations

from typing import TYPE_CHECKING

from .bytecode_transformation import types
from .ceval import PyEval

if TYPE_CHECKING:
    pass


class OutputGraph:
    def __init__(
        self,
        frame: types.FrameType,
        compiler_fn: callable,
        root_tx: PyEval,
    ):
        pass
