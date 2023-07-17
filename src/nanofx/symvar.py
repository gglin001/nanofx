from __future__ import annotations

import inspect
import itertools
import operator

from typing import TYPE_CHECKING, Any, Callable

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
        assert isinstance(self.var, Callable)
        var = self.var
        graph = tx.output.graph

        if var.__module__.startswith("paddle"):
            # TODO: support multiple ouputs and containers
            return SymVar(vtype=args[0].vtype)
        elif inspect.isbuiltin(var):
            if var is print:
                raise NotImplementedError("print() is not supported")
            elif var is getattr:
                object, name = args
                attr = getattr(object.var, name.var)
                return SymVar(var=attr)
            elif var is operator.add:
                ot = args[0].vtype
                graph.call_function(var, args, kwargs, ot)
                return SymVar(vtype=ot)
            elif var is operator.sub:
                return SymVar(vtype=args[0].vtype)
            else:
                raise NotImplementedError(f"builtin {var} is not supported")

        return tx.inline_call_function(self, args, kwargs)
