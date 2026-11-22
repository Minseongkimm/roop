import unittest
from src.prefix import strip_prefix


class TestStripPrefix(unittest.TestCase):
    def test_strip(self) -> None:
        self.assertEqual(strip_prefix("prefix-value", "prefix-"), "value")
        self.assertEqual(strip_prefix("value", "prefix-"), "value")
        self.assertEqual(strip_prefix("abc", ""), "abc")
        self.assertEqual(strip_prefix("aaa", "a"), "aa")


if __name__ == "__main__":
    unittest.main()
