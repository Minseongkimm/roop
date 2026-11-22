import unittest
from src.chunk import chunk_list


class TestChunk(unittest.TestCase):
    def test_chunks(self) -> None:
        self.assertEqual(chunk_list([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            chunk_list([1], 0)


if __name__ == "__main__":
    unittest.main()
