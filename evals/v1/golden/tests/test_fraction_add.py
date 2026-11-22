import unittest
from src.frac_math import add_fractions
from src.fraction import reduce_fraction


class TestFraction(unittest.TestCase):
    def test_reduce(self) -> None:
        self.assertEqual(reduce_fraction(2, 4), (1, 2))
        self.assertEqual(reduce_fraction(2, -4), (-1, 2))
        self.assertEqual(reduce_fraction(-2, -4), (1, 2))
        self.assertEqual(reduce_fraction(0, -3), (0, 1))

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            reduce_fraction(1, 0)
        with self.assertRaises(ValueError):
            reduce_fraction(True, 2)

    def test_add(self) -> None:
        self.assertEqual(add_fractions((1, 2), (1, 3)), (5, 6))
        self.assertEqual(add_fractions((1, 2), (-1, 2)), (0, 1))


if __name__ == "__main__":
    unittest.main()
