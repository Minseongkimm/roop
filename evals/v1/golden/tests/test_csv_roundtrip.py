import unittest

from src.csv_read import parse_csv
from src.csv_write import write_csv


class TestCsvRoundtrip(unittest.TestCase):
    def test_quotes_roundtrip(self) -> None:
        rows = [{"name": "a,b", "note": 'say "hi"'}]
        text = write_csv(rows, ["name", "note"])
        self.assertEqual(parse_csv(text), rows)

    def test_header_only_and_empty(self) -> None:
        self.assertEqual(parse_csv(""), [])
        self.assertEqual(parse_csv("\n"), [])
        self.assertEqual(parse_csv("name,note\n"), [])
        written = write_csv([], ["name", "note"])
        self.assertEqual(written, "name,note\n")

    def test_short_row_and_embedded_newline(self) -> None:
        parsed = parse_csv('name,note\n"hello\nworld",\n')
        self.assertEqual(parsed, [{"name": "hello\nworld", "note": ""}])

    def test_duplicate_header_and_extra_field(self) -> None:
        with self.assertRaises(ValueError):
            parse_csv("a,a\n1,2\n")
        with self.assertRaises(ValueError):
            parse_csv("a,b\n1,2,3\n")
        with self.assertRaises(ValueError):
            write_csv([], [])


if __name__ == "__main__":
    unittest.main()
