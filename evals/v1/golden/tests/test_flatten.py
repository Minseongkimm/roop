import unittest
from src.flatten import flatten_once


class TestFlatten(unittest.TestCase):
    def test_one_level(self) -> None:
        self.assertEqual(flatten_once([1, [2, 3], [4]]), [1, 2, 3, 4])

    def test_deeper_stays(self) -> None:
        self.assertEqual(flatten_once([1, [2, [3]]]), [1, 2, [3]])


if __name__ == "__main__":
    unittest.main()
