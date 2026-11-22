import unittest
from src.kv import parse_kv


class TestKV(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(parse_kv("key=value"), {"key": "value"})

    def test_multiline_and_comments(self) -> None:
        text = "#c\na=b\n\nc=d\na=z\n"
        self.assertEqual(parse_kv(text), {"a": "z", "c": "d"})


if __name__ == "__main__":
    unittest.main()
