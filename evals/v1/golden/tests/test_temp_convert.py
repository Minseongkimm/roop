import unittest
from src.temp_convert import convert_temp
from src.temp_parse import parse_temp


class TestTemp(unittest.TestCase):
    def test_convert(self) -> None:
        self.assertEqual(parse_temp("32F"), (32.0, "F"))
        self.assertEqual(parse_temp("10 c"), (10.0, "C"))
        self.assertEqual(convert_temp("32F", "C"), "0.0C")
        self.assertEqual(convert_temp("100C", "F"), "212.0F")
        self.assertEqual(convert_temp("100C", "c"), "100.0C")

    def test_invalid(self) -> None:
        for text in ("", "12", "12K"):
            with self.assertRaises(ValueError):
                parse_temp(text)
        with self.assertRaises(ValueError):
            convert_temp("0C", "K")


if __name__ == "__main__":
    unittest.main()
