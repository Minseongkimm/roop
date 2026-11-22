import unittest
from src.word_count import word_count


class TestWordCount(unittest.TestCase):
    def test_counts(self) -> None:
        self.assertEqual(word_count("A a, b!"), {"a": 2, "b": 1})
        self.assertEqual(word_count(""), {})
        self.assertEqual(word_count("py3 py3"), {"py3": 2})


if __name__ == "__main__":
    unittest.main()
