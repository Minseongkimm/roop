import unittest

from src.filters import apply_filter
from src.template import render


class TestFilters(unittest.TestCase):
    def test_known_filters(self) -> None:
        self.assertEqual(apply_filter("Ab", "upper"), "AB")
        self.assertEqual(apply_filter("Ab", "lower"), "ab")
        self.assertEqual(apply_filter("", "default", "guest"), "guest")
        self.assertEqual(apply_filter("a", "default", "guest"), "a")

    def test_unknown_filter(self) -> None:
        with self.assertRaises(ValueError):
            apply_filter("a", "nope")


class TestTemplate(unittest.TestCase):
    def test_render(self) -> None:
        self.assertEqual(render("Hi {{ name }}", {"name": "Sam"}), "Hi Sam")
        self.assertEqual(render("{{ name|upper }}", {"name": "Sam"}), "SAM")
        self.assertEqual(render("{{ name|default:guest }}", {}), "guest")
        self.assertEqual(render("x {{ name|default: }} y", {}), "x  y")
        self.assertEqual(render("no tags", {}), "no tags")

    def test_errors(self) -> None:
        with self.assertRaises(KeyError):
            render("{{ name }}", {})
        with self.assertRaises(ValueError):
            render("{{ name|nope }}", {"name": "a"})
        with self.assertRaises(ValueError):
            render("{{ name", {"name": "a"})


if __name__ == "__main__":
    unittest.main()
