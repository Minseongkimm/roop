import unittest
from src.zip_strict import zip_strict


class TestZipStrict(unittest.TestCase):
    def test_zip(self) -> None:
        left = [1, 2]
        right = ["a", "b"]
        self.assertEqual(zip_strict(left, right), [(1, "a"), (2, "b")])
        self.assertEqual(left, [1, 2])
        self.assertEqual(right, ["a", "b"])
        self.assertEqual(zip_strict([], []), [])

    def test_length(self) -> None:
        with self.assertRaises(ValueError):
            zip_strict([1], [])


if __name__ == "__main__":
    unittest.main()
