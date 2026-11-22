import unittest
from src.pad import pad_left


class TestPadLeft(unittest.TestCase):
    def test_pad(self) -> None:
        self.assertEqual(pad_left("7", 3, "0"), "007")
        self.assertEqual(pad_left("abcd", 3), "abcd")
        self.assertEqual(pad_left("", 2), "  ")
        self.assertEqual(pad_left("a", 0), "a")

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            pad_left("a", -1)
        with self.assertRaises(ValueError):
            pad_left("a", 2, "ab")
        with self.assertRaises(ValueError):
            pad_left("a", True)


if __name__ == "__main__":
    unittest.main()
