import unittest
from src.line_stats import count_nonempty
from src.lines import split_lines


class TestLineStats(unittest.TestCase):
    def test_lines(self) -> None:
        self.assertEqual(split_lines("a\nb\n"), ["a", "b"])
        self.assertEqual(split_lines("a\n\nb"), ["a", "", "b"])
        self.assertEqual(split_lines(""), [])
        self.assertEqual(count_nonempty("a\n\nb\n"), 2)
        self.assertEqual(count_nonempty("  \n"), 0)


if __name__ == "__main__":
    unittest.main()
