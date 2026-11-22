import unittest
from src.digits import digit_sum


class TestDigitSum(unittest.TestCase):
    def test_sum(self) -> None:
        self.assertEqual(digit_sum(0), 0)
        self.assertEqual(digit_sum(405), 9)
        self.assertEqual(digit_sum(8), 8)

    def test_invalid(self) -> None:
        for value in (-1, True, "4"):
            with self.assertRaises(ValueError):
                digit_sum(value)


if __name__ == "__main__":
    unittest.main()
