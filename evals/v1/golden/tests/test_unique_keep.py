import unittest
from src.unique import unique_keep


class TestUniqueKeep(unittest.TestCase):
    def test_order_and_input(self) -> None:
        source = ["b", "a", "b", "a", "c"]
        self.assertEqual(unique_keep(source), ["b", "a", "c"])
        self.assertEqual(source, ["b", "a", "b", "a", "c"])
        self.assertEqual(unique_keep([]), [])
        self.assertEqual(unique_keep([1, 1, 1]), [1])


if __name__ == "__main__":
    unittest.main()
