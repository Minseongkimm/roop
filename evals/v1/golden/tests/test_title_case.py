import unittest
from src.title_case import title_case


class TestTitleCase(unittest.TestCase):
    def test_words(self) -> None:
        self.assertEqual(title_case("hello WORLD"), "Hello World")
        self.assertEqual(title_case("a  b"), "A B")
        self.assertEqual(title_case(""), "")
        self.assertEqual(title_case("   "), "")
        self.assertEqual(title_case("py"), "Py")


if __name__ == "__main__":
    unittest.main()
