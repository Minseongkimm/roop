import unittest
from src.ring import Ring
from src.window import last_n


class TestRingWindow(unittest.TestCase):
    def test_ring(self) -> None:
        ring = Ring(2)
        ring.push("a")
        ring.push("b")
        ring.push("c")
        self.assertEqual(ring.items(), ["b", "c"])
        self.assertEqual(ring.size(), 2)
        self.assertEqual(last_n(ring, 1), ["c"])
        self.assertEqual(last_n(ring, 5), ["b", "c"])

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            Ring(0)
        with self.assertRaises(ValueError):
            Ring(True)
        with self.assertRaises(ValueError):
            last_n(Ring(1), 0)


if __name__ == "__main__":
    unittest.main()
