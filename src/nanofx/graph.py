from __future__ import annotations

from typing import Any, Callable


class Node:
    def __init__(
        self,
        *,
        graph: Graph,
        name: str,
        op: str,
        target: Callable[..., Any] | str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        return_type: Any | None = None,
    ) -> None:
        self.graph = graph
        self.name = name
        assert op in [
            'placeholder',
            'call_method',
            'call_module',
            'call_function',
            'get_attr',
            'output',
            'root',
        ]
        self.op = op
        if op == 'call_function':
            assert isinstance(target, Callable)
        else:
            assert isinstance(target, str)

        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.type: Any | None = return_type

        self.meta: dict[str, Any] = {}


class Graph:
    def __init__(self):
        self._codegen = CodeGen()

        # TODO: make it more like torch
        self.nodes: list[Node] = []

    def create_node(
        self,
        op: str,
        target: Callable[..., Any] | str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] = {},
        name: str | None = None,
        type_expr: Any | None = None,
    ) -> Node:
        assert op in (
            'call_function',
            'call_method',
            'get_attr',
            'call_module',
            'placeholder',
            'output',
        )
        n = Node(
            graph=self,
            name=name,
            op=op,
            target=target,
            args=args,
            kwargs=kwargs,
            return_type=type_expr,
        )
        self.nodes.append(n)
        return n


class CodeGen:
    def __init__(self):
        pass
