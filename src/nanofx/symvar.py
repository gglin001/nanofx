from __future__ import annotations

import inspect
import itertools
import operator

from typing import TYPE_CHECKING, Any, Callable

from .paddle_utils import Layer, Sequential
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

        if hasattr(var, '__qualname__') and var.__qualname__ == 'OrderedDict.values':
            values = var()
            return SymVar(var=values)

        if var.__module__ is not None and var.__module__.startswith("paddle"):
            # TODO: support multiple ouputs and containers
            # Sequential
            if isinstance(var, Sequential):
                for layer in var:
                    tx.call_function(SymVar(var=layer), args=args, kwargs=kwargs)
            elif var.__module__.startswith('paddle.vision.models.resnet'):
                raise NotImplementedError("resnet is not supported")
                # do inline call
                # return tx.inline_call_function(SymVar(var=var.forward), args, kwargs)
            else:
                ot = args[0].vtype
                graph.call_function(var, args, kwargs, ot)
                return SymVar(vtype=ot)
        elif inspect.isbuiltin(var):
            if var is print:
                raise NotImplementedError("print() is not supported")
            elif var is getattr:
                object, name = args
                attr = getattr(object.var, name.var)
                return SymVar(var=attr)
            elif var is iter:
                target = args[0]
                var = iter(target.var)
                return SymVar(var=var)
            elif var in [operator.add, operator.sub, operator.iadd]:
                ot = args[0].vtype
                graph.call_function(var, args, kwargs, ot)
                return SymVar(vtype=ot)
            elif var in [operator.gt, operator.is_not]:
                ot = args[0].vtype
                graph.call_function(var, args, kwargs, ot)
                return SymVar(vtype=ot)
            else:
                raise NotImplementedError(f"builtin {var} is not supported")

        if isinstance(var, Layer):
            return tx.inline_call_function(SymVar(var=var.forward), args, kwargs)
        return tx.inline_call_function(self, args, kwargs)
