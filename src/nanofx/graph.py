from __future__ import annotations

from typing import Any, Callable


class Node:
    def __init__(
        self,
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
        self.type: Any | None = return_type


class CodeGen:
    def __init__(self):
        pass


class Graph:
    def __init__(self):
        self._root: Node = Node(self, '', 'root', '', (), {})
        self._codegen = CodeGen()
