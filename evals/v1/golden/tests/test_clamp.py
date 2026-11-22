import unittest
from src.clamp import clamp


class TestClamp(unittest.TestCase):
    def test_within_range(self) -> None:
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_below_low(self) -> None:
        self.assertEqual(clamp(-1, 0, 10), 0)

    def test_above_high(self) -> None:
        self.assertEqual(clamp(99, 0, 10), 10)

    def test_invalid_range(self) -> None:
        with self.assertRaises(ValueError):
            clamp(1, 5, 2)


if __name__ == "__main__":
    unittest.main()
