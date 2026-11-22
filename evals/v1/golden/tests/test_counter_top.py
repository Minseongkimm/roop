import unittest
from src.counter_top import top_n


class TestCounterTop(unittest.TestCase):
    def test_top_n(self) -> None:
        actual = top_n(["a", "b", "a"], 2)
        self.assertEqual(actual[0], ("a", 2))
        self.assertEqual(len(actual), 2)

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            top_n(["a"], 0)


if __name__ == "__main__":
    unittest.main()
