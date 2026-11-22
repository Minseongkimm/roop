import unittest
from src.words import reverse_words


class TestReverseWords(unittest.TestCase):
    def test_order(self) -> None:
        self.assertEqual(reverse_words("Hello World"), "World Hello")
        self.assertEqual(reverse_words("a  b\tc"), "c b a")
        self.assertEqual(reverse_words("only"), "only")

    def test_blank(self) -> None:
        self.assertEqual(reverse_words(""), "")
        self.assertEqual(reverse_words("   "), "")


if __name__ == "__main__":
    unittest.main()
