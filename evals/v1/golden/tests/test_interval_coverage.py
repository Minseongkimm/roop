import unittest

from src.coverage import covered_length
from src.intervals import merge_intervals


class TestIntervals(unittest.TestCase):
    def test_merge_without_mutating(self) -> None:
        raw = [[8, 10], [1, 3], [2, 6]]
        self.assertEqual(merge_intervals(raw), [[1, 6], [8, 10]])
        self.assertEqual(raw, [[8, 10], [1, 3], [2, 6]])
        self.assertEqual(merge_intervals([[1, 2], [2, 3]]), [[1, 3]])
        self.assertEqual(merge_intervals([[1, 2], [4, 5]]), [[1, 2], [4, 5]])
        self.assertEqual(merge_intervals([]), [])

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            merge_intervals([[3, 1]])


class TestCoverage(unittest.TestCase):
    def test_inclusive_length_after_merge(self) -> None:
        self.assertEqual(covered_length([[1, 1]]), 1)
        self.assertEqual(covered_length([[1, 3], [2, 6], [8, 10]]), 9)
        self.assertEqual(covered_length([]), 0)


if __name__ == "__main__":
    unittest.main()
