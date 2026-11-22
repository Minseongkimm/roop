import unittest
from src.roman_format import format_roman
from src.roman_parse import parse_roman


class TestRoman(unittest.TestCase):
    def test_roundtrip(self) -> None:
        self.assertEqual(format_roman(4), "IV")
        self.assertEqual(format_roman(9), "IX")
        self.assertEqual(format_roman(1994), "MCMXCIV")
        self.assertEqual(parse_roman("III"), 3)
        self.assertEqual(parse_roman("MCMXCIV"), 1994)
        self.assertEqual(format_roman(parse_roman("XLII")), "XLII")

    def test_invalid(self) -> None:
        for text in ("", "iiii", "IIII", "IC"):
            with self.assertRaises(ValueError):
                parse_roman(text)
        for value in (0, 4000, True):
            with self.assertRaises(ValueError):
                format_roman(value)


if __name__ == "__main__":
    unittest.main()
