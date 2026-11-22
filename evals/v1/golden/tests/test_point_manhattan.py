import unittest
from src.distance import manhattan
from src.point import Point


class TestPoint(unittest.TestCase):
    def test_distance(self) -> None:
        self.assertEqual(manhattan(Point(0, 0), Point(3, -1)), 4)
        self.assertEqual(manhattan(Point(1, 1), Point(1, 1)), 0)

    def test_types(self) -> None:
        with self.assertRaises(TypeError):
            Point(True, 1)
        with self.assertRaises(TypeError):
            manhattan(Point(0, 0), (1, 1))


if __name__ == "__main__":
    unittest.main()
