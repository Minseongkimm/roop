import unittest
from src.wrap import wrap_text


class TestWrapText(unittest.TestCase):
    def test_wrap(self) -> None:
        self.assertEqual(wrap_text("one two three", 7), ["one two", "three"])
        self.assertEqual(wrap_text("abcd ef", 3), ["abcd", "ef"])
        self.assertEqual(wrap_text("  ", 4), [])
        self.assertEqual(wrap_text("", 4), [])

    def test_width(self) -> None:
        with self.assertRaises(ValueError):
            wrap_text("a", 0)
        with self.assertRaises(ValueError):
            wrap_text("a", True)


if __name__ == "__main__":
    unittest.main()
