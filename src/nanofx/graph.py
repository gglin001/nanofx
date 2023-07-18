from __future__ import annotations

from typing import Any, Callable


class Node:
    def __init__(
        self,
        *,
        graph: Graph,
        name: str | None,
        op: str,
        target: Callable[..., Any] | str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        return_type: Any | None = None,
    ) -> None:
        assert op in [
            'placeholder',
            'call_method',
            'call_module',
            'call_function',
            'get_attr',
            'output',
            'root',
        ]

        self.graph = graph
        self.name = name
        self.op = op
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.return_type = return_type

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
        return_type: Any | None = None,
    ) -> Node:
        node = Node(
            graph=self,
            name=name,
            op=op,
            target=target,
            args=args,
            kwargs=kwargs,
            return_type=return_type,
        )
        self.nodes.append(node)
        return node

    def placeholder(
        self,
        target: str,
        return_type: Any = None,
        default_value: Any = None,
    ) -> Node:
        args = () if default_value is None else (default_value,)
        return self.create_node(
            op='placeholder',
            target=target,
            args=args,
            return_type=return_type,
        )

    def call_function(
        self,
        target: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] = {},
        return_type: Any | None = None,
    ) -> Node:
        return self.create_node(
            op='call_function',
            target=target,
            args=args,
            kwargs=kwargs,
            return_type=return_type,
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
