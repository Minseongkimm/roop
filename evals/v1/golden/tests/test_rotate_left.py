import unittest
from src.rotate import rotate_left


class TestRotateLeft(unittest.TestCase):
    def test_rotate(self) -> None:
        source = [1, 2, 3, 4]
        self.assertEqual(rotate_left(source, 1), [2, 3, 4, 1])
        self.assertEqual(rotate_left(source, -1), [4, 1, 2, 3])
        self.assertEqual(rotate_left(source, 5), [2, 3, 4, 1])
        self.assertEqual(source, [1, 2, 3, 4])
        self.assertEqual(rotate_left([], 3), [])

    def test_steps(self) -> None:
        with self.assertRaises(ValueError):
            rotate_left([1], True)


if __name__ == "__main__":
    unittest.main()
