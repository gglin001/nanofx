from __future__ import annotations

import inspect
import itertools
import operator

from typing import TYPE_CHECKING, Any

from .source import Source

_sym_var_id_counter = itertools.count()

if TYPE_CHECKING:
    from .pyeval import PyEvalBase


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
        # TODO: better org
        if inspect.isbuiltin(self.var):
            if self.var is print:
                raise NotImplementedError("print() is not supported")
            elif self.var is operator.add:
                return SymVar(vtype=args[0].vtype)
            elif self.var is operator.sub:
                return SymVar(vtype=args[0].vtype)
            else:
                raise NotImplementedError(f"builtin {self.var} is not supported")

        return tx.inline_call_function(self, args, kwargs)
