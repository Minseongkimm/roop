import unittest
from src.safe_div import safe_div


class TestSafeDiv(unittest.TestCase):
    def test_normal(self) -> None:
        self.assertEqual(safe_div(10, 2), 5)

    def test_zero_default(self) -> None:
        self.assertEqual(safe_div(1, 0, 0), 0)

    def test_zero_none(self) -> None:
        self.assertIsNone(safe_div(1, 0))


if __name__ == "__main__":
    unittest.main()
