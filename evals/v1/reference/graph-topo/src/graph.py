"""Directed graph. An edge means the source comes before the target."""

from __future__ import annotations


class Graph:
    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self._edges: set[tuple[str, str]] = set()

    def add_node(self, name: str) -> None:
        if name == "":
            raise ValueError("node name is required")
        self._nodes.add(name)

    def add_edge(self, source: str, target: str) -> None:
        self.add_node(source)
        self.add_node(target)
        self._edges.add((source, target))

    def nodes(self) -> list[str]:
        return sorted(self._nodes)

    def successors(self, name: str) -> list[str]:
        if name not in self._nodes:
            raise KeyError(name)
        return sorted(target for source, target in self._edges if source == name)

    def predecessors(self, name: str) -> list[str]:
        if name not in self._nodes:
            raise KeyError(name)
        return sorted(source for source, target in self._edges if target == name)
