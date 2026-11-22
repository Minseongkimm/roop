import unittest
from src.scanner import scan_words
from src.token import is_word_token


class TestTokenScan(unittest.TestCase):
    def test_token(self) -> None:
        self.assertTrue(is_word_token("Ab"))
        self.assertFalse(is_word_token("A1"))
        self.assertFalse(is_word_token(""))

    def test_scan(self) -> None:
        self.assertEqual(scan_words("Hello, World 2nd"), ["hello", "world", "nd"])
        self.assertEqual(scan_words(""), [])
        self.assertEqual(scan_words("123"), [])


if __name__ == "__main__":
    unittest.main()
