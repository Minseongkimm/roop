import unittest
from src.spaces import collapse_spaces


class TestCollapseSpaces(unittest.TestCase):
    def test_collapse(self) -> None:
        self.assertEqual(collapse_spaces("  a\t\nb "), "a b")
        self.assertEqual(collapse_spaces(""), "")
        self.assertEqual(collapse_spaces("   "), "")
        self.assertEqual(collapse_spaces("ab"), "ab")


if __name__ == "__main__":
    unittest.main()
