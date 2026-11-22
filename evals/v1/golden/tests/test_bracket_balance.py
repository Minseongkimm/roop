import unittest
from src.brackets import is_balanced


class TestBrackets(unittest.TestCase):
    def test_balanced(self) -> None:
        self.assertTrue(is_balanced(""))
        self.assertTrue(is_balanced("([a])"))
        self.assertTrue(is_balanced("no brackets"))

    def test_unbalanced(self) -> None:
        self.assertFalse(is_balanced("("))
        self.assertFalse(is_balanced("([)]"))
        self.assertFalse(is_balanced("]"))
        self.assertFalse(is_balanced("(())]"))


if __name__ == "__main__":
    unittest.main()
