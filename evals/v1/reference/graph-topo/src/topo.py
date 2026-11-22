"""Stable topological sort. Ready nodes are chosen in lexicographic order."""

from __future__ import annotations

from src.graph import Graph


def topo_sort(graph: Graph) -> list[str]:
    indegree: dict[str, int] = {name: 0 for name in graph.nodes()}
    for name in graph.nodes():
        for successor in graph.successors(name):
            indegree[successor] = indegree.get(successor, 0) + 1
    ready: list[str] = sorted(name for name, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        current: str = ready.pop(0)
        ordered.append(current)
        for successor in graph.successors(current):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
        ready.sort()
    if len(ordered) != len(indegree):
        raise ValueError("graph has a cycle")
    return ordered
