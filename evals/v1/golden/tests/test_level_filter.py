import unittest
from src.level import parse_level
from src.level_filter import filter_lines


class TestLevelFilter(unittest.TestCase):
    def test_filter(self) -> None:
        self.assertEqual(parse_level("WARN"), 30)
        source = ["debug a", "info b", "error c"]
        self.assertEqual(filter_lines(source, "warn"), ["error c"])
        self.assertEqual(source, ["debug a", "info b", "error c"])
        self.assertEqual(filter_lines(["info hello"], "info"), ["info hello"])

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            parse_level("trace")
        with self.assertRaises(ValueError):
            filter_lines(["nope"], "info")
        with self.assertRaises(ValueError):
            filter_lines(["info   "], "info")


if __name__ == "__main__":
    unittest.main()
