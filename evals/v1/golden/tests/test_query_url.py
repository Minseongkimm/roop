import unittest

from src.query import build_query, parse_query
from src.url_parts import split_url


class TestQuery(unittest.TestCase):
    def test_parse_and_build(self) -> None:
        self.assertEqual(parse_query(""), {})
        self.assertEqual(parse_query("?q=a+b&q=c%20d"), {"q": "c d"})
        self.assertEqual(parse_query("flag"), {"flag": ""})
        self.assertEqual(build_query({"b": "x y", "a": "1"}), "a=1&b=x%20y")
        self.assertEqual(parse_query(build_query({"a": "1"})), {"a": "1"})
        self.assertEqual(build_query({}), "")

    def test_empty_key(self) -> None:
        with self.assertRaises(ValueError):
            parse_query("=1")


class TestUrl(unittest.TestCase):
    def test_split(self) -> None:
        self.assertEqual(
            split_url("https://ex.com:8080/a/b?x=1#top"),
            {"scheme": "https", "host": "ex.com:8080", "path": "/a/b", "query": "x=1"},
        )
        self.assertEqual(
            split_url("/a/b?x=1"),
            {"scheme": "", "host": "", "path": "/a/b", "query": "x=1"},
        )
        self.assertEqual(
            split_url("https://ex.com"),
            {"scheme": "https", "host": "ex.com", "path": "", "query": ""},
        )

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            split_url("ex.com/a")
        with self.assertRaises(ValueError):
            split_url("https://user@ex.com/a")


if __name__ == "__main__":
    unittest.main()
