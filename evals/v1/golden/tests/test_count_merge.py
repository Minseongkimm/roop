import unittest
from src.count_merge import merge_counts
from src.counts import parse_counts


class TestCounts(unittest.TestCase):
    def test_parse_and_merge(self) -> None:
        self.assertEqual(parse_counts(""), {})
        self.assertEqual(parse_counts("a:1,a:2"), {"a": 3})
        self.assertEqual(merge_counts(["a:1", "a:4,b:1"]), {"a": 5, "b": 1})
        self.assertEqual(merge_counts([]), {})

    def test_invalid(self) -> None:
        for text in ("a", "a:-1", ":1", "a:1.5"):
            with self.assertRaises(ValueError):
                parse_counts(text)


if __name__ == "__main__":
    unittest.main()
