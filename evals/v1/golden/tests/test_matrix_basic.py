import unittest
from src.matmul import multiply
from src.matrix import transpose


class TestMatrix(unittest.TestCase):
    def test_transpose(self) -> None:
        source = [[1, 2], [3, 4]]
        self.assertEqual(transpose(source), [[1, 3], [2, 4]])
        self.assertEqual(source, [[1, 2], [3, 4]])
        self.assertEqual(transpose([]), [])
        with self.assertRaises(ValueError):
            transpose([[1, 2], [3]])

    def test_multiply(self) -> None:
        self.assertEqual(multiply([[1, 2], [3, 4]], [[1, 0], [0, 1]]), [[1, 2], [3, 4]])
        self.assertEqual(multiply([[1, 2]], [[3], [4]]), [[11]])
        with self.assertRaises(ValueError):
            multiply([[1, 2]], [[1]])


if __name__ == "__main__":
    unittest.main()
