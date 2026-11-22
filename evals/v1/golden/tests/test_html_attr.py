import unittest
from src.html_attr import render_attr
from src.html_escape import escape_text


class TestHtmlAttr(unittest.TestCase):
    def test_escape(self) -> None:
        self.assertEqual(escape_text("a<b &"), "a&lt;b &amp;")
        self.assertEqual(escape_text("\"'"), "&quot;&#39;")
        self.assertEqual(render_attr("title", "a<b &"), "title=\"a&lt;b &amp;\"")

    def test_name(self) -> None:
        with self.assertRaises(ValueError):
            render_attr("1bad", "x")
        with self.assertRaises(ValueError):
            render_attr("", "x")


if __name__ == "__main__":
    unittest.main()
