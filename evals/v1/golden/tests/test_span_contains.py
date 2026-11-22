import unittest
from src.span import parse_span
from src.span_query import span_contains


class TestSpan(unittest.TestCase):
    def test_span(self) -> None:
        self.assertEqual(parse_span("1-5"), (1, 5))
        self.assertEqual(parse_span("3"), (3, 3))
        self.assertTrue(span_contains("1-5", 1))
        self.assertTrue(span_contains("1-5", 5))
        self.assertFalse(span_contains("1-5", 6))

    def test_invalid(self) -> None:
        for text in ("5-1", "a-b", "", "1-"):
            with self.assertRaises(ValueError):
                parse_span(text)
        with self.assertRaises(ValueError):
            span_contains("1-2", True)


if __name__ == "__main__":
    unittest.main()
