import unittest

from src.ini_dump import dump_ini
from src.ini_parse import parse_ini


class TestIniRoundtrip(unittest.TestCase):
    def test_parse_comments_and_duplicates(self) -> None:
        text = "# c\n\nkey=before\n[app]\nname = demo\n; skip\nname = next\n[db]\nport=1\n"
        parsed = parse_ini(text)
        self.assertEqual(parsed[""]["key"], "before")
        self.assertEqual(parsed["app"]["name"], "next")
        self.assertEqual(parsed["db"]["port"], "1")

    def test_roundtrip(self) -> None:
        data = {"": {"a": "1"}, "b": {"d": "3", "c": "2"}}
        self.assertEqual(parse_ini(dump_ini(data)), data)
        self.assertEqual(dump_ini({}), "")
        self.assertEqual(parse_ini(""), {})

    def test_bad_line(self) -> None:
        with self.assertRaises(ValueError):
            parse_ini("[app]\nnot a pair\n")


if __name__ == "__main__":
    unittest.main()
