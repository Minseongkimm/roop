import unittest
from src.path_clean import clean_segment
from src.path_join import join_path


class TestPathJoin(unittest.TestCase):
    def test_join(self) -> None:
        self.assertEqual(clean_segment(" a "), "a")
        self.assertEqual(join_path([" a ", "b"]), "a/b")

    def test_invalid(self) -> None:
        for segment in ("", ".", "..", "a/b", "a\\b", "  "):
            with self.assertRaises(ValueError):
                clean_segment(segment)
        with self.assertRaises(ValueError):
            join_path([])
        with self.assertRaises(ValueError):
            join_path(["ok", ".."])


if __name__ == "__main__":
    unittest.main()
