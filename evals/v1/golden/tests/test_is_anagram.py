import unittest
from src.anagram import is_anagram


class TestAnagram(unittest.TestCase):
    def test_pairs(self) -> None:
        self.assertTrue(is_anagram("Dormitory", "dirty room"))
        self.assertTrue(is_anagram("", ""))
        self.assertTrue(is_anagram("A1!", "1a"))
        self.assertFalse(is_anagram("ab", "a"))
        self.assertFalse(is_anagram("ab", "ac"))


if __name__ == "__main__":
    unittest.main()
