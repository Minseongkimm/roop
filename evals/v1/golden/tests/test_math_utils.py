import unittest
from src.math_utils import mean, median


class TestMathUtils(unittest.TestCase):
    def test_mean(self) -> None:
        self.assertEqual(mean([1, 2, 3]), 2)
        with self.assertRaises(ValueError):
            mean([])

    def test_median(self) -> None:
        self.assertEqual(median([1, 2, 3]), 2)
        self.assertEqual(median([1, 2, 3, 4]), 2.5)
        with self.assertRaises(ValueError):
            median([])

    def test_no_mutate(self) -> None:
        values = [3, 1, 2]
        original = list(values)
        mean(values)
        median(values)
        self.assertEqual(values, original)


if __name__ == "__main__":
    unittest.main()
