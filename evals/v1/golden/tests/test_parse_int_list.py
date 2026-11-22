import unittest
from src.int_list import parse_int_list


class TestParseIntList(unittest.TestCase):
    def test_values(self) -> None:
        self.assertEqual(parse_int_list("1, 2, -3"), [1, 2, -3])
        self.assertEqual(parse_int_list(""), [])
        self.assertEqual(parse_int_list("   "), [])
        self.assertEqual(parse_int_list("8"), [8])

    def test_invalid(self) -> None:
        for text in ("1,,2", "1.5", "+1", "a", "1, "):
            with self.assertRaises(ValueError):
                parse_int_list(text)


if __name__ == "__main__":
    unittest.main()
