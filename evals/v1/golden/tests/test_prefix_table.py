import unittest
from src.prefix_norm import normalize_key
from src.prefix_table import PrefixTable


class TestPrefixTable(unittest.TestCase):
    def test_table(self) -> None:
        self.assertEqual(normalize_key("  A   B "), "a b")
        table = PrefixTable()
        table.add("A B", 1)
        table.add("a   b", 2)
        self.assertEqual(table.get(" a b "), 2)
        with self.assertRaises(KeyError):
            table.get("missing")
        with self.assertRaises(ValueError):
            normalize_key("   ")


if __name__ == "__main__":
    unittest.main()
