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

    def placeholder(
        self,
        name: str,
        type_expr: Any = None,
        default_value: Any = None,
    ) -> Node:
        args = () if default_value is None else (default_value,)
        return self.create_node('placeholder', name, args=args, type_expr=type_expr)

    def call_function(
        self,
        the_function: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] = {},
        type_expr: Any | None = None,
    ) -> Node:
        return self.create_node(
            'call_function', the_function, args, kwargs, type_expr=type_expr
        )

    def print_tabular(self):
        from tabulate import tabulate

        node_specs = [[n.op, n.name, n.target, n.args, n.kwargs] for n in self.nodes]
        print(
            tabulate(node_specs, headers=['opcode', 'name', 'target', 'args', 'kwargs'])
        )


class CodeGen:
    def __init__(self):
        pass
