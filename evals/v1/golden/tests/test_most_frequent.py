import unittest
from src.frequent import most_frequent


class TestMostFrequent(unittest.TestCase):
    def test_choice(self) -> None:
        source = ["b", "a", "b", "a"]
        self.assertEqual(most_frequent(source), "b")
        self.assertEqual(source, ["b", "a", "b", "a"])
        self.assertEqual(most_frequent(["x"]), "x")
        self.assertEqual(most_frequent([2, 1, 1]), 1)

    def test_empty(self) -> None:
        with self.assertRaises(ValueError):
            most_frequent([])


if __name__ == "__main__":
    unittest.main()
