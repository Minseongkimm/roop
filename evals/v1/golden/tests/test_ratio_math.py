import unittest
from src.ratio import parse_ratio
from src.ratio_math import multiply_ratios


class TestRatio(unittest.TestCase):
    def test_ratio(self) -> None:
        self.assertEqual(parse_ratio("2/4"), (1, 2))
        self.assertEqual(parse_ratio("3"), (3, 1))
        self.assertEqual(parse_ratio("0/2"), (0, 1))
        self.assertEqual(parse_ratio("-2/4"), (-1, 2))
        self.assertEqual(multiply_ratios("1/2", "2/3"), (1, 3))

    def test_invalid(self) -> None:
        for text in ("2/0", "a/b", "", "1/"):
            with self.assertRaises(ValueError):
                parse_ratio(text)


if __name__ == "__main__":
    unittest.main()
