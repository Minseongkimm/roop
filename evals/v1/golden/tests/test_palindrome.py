import unittest
from src.palindrome import is_palindrome


class TestPalindrome(unittest.TestCase):
    def test_classic(self) -> None:
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama"))

    def test_empty(self) -> None:
        self.assertTrue(is_palindrome(""))

    def test_false(self) -> None:
        self.assertFalse(is_palindrome("hello"))


if __name__ == "__main__":
    unittest.main()
