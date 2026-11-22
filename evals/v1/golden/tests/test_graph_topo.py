import unittest

from src.graph import Graph
from src.topo import topo_sort


class TestGraphTopo(unittest.TestCase):
    def test_stable_order(self) -> None:
        graph = Graph()
        graph.add_edge("b", "c")
        graph.add_edge("a", "c")
        graph.add_node("d")
        self.assertEqual(graph.nodes(), ["a", "b", "c", "d"])
        self.assertEqual(topo_sort(graph), ["a", "b", "c", "d"])

    def test_cycle_and_self_loop(self) -> None:
        cycle = Graph()
        cycle.add_edge("a", "b")
        cycle.add_edge("b", "a")
        with self.assertRaises(ValueError):
            topo_sort(cycle)
        loop = Graph()
        loop.add_edge("a", "a")
        with self.assertRaises(ValueError):
            topo_sort(loop)

    def test_duplicates_unknown_and_empty(self) -> None:
        graph = Graph()
        graph.add_edge("a", "b")
        graph.add_edge("a", "b")
        self.assertEqual(graph.successors("a"), ["b"])
        self.assertEqual(graph.predecessors("b"), ["a"])
        with self.assertRaises(KeyError):
            graph.successors("missing")
        with self.assertRaises(ValueError):
            graph.add_node("")
        self.assertEqual(topo_sort(Graph()), [])


if __name__ == "__main__":
    unittest.main()
