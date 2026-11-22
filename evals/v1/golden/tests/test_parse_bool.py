import unittest
from src.bools import parse_bool


class TestParseBool(unittest.TestCase):
    def test_values(self) -> None:
        self.assertTrue(parse_bool(" YES "))
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("1"))
        self.assertFalse(parse_bool("No"))
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool("0"))

    def test_invalid(self) -> None:
        for text in ("", "maybe", "2", "trueish"):
            with self.assertRaises(ValueError):
                parse_bool(text)


if __name__ == "__main__":
    unittest.main()
