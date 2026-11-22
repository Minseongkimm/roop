import unittest
from src.url_path import join_url_path


class TestJoinUrlPath(unittest.TestCase):
    def test_join(self) -> None:
        self.assertEqual(join_url_path("a", "/b/", "c"), "a/b/c")
        self.assertEqual(join_url_path("/a", "b"), "/a/b")
        self.assertEqual(join_url_path("", "  "), "")
        self.assertEqual(join_url_path(), "")
        self.assertEqual(join_url_path(" a ", "b"), "a/b")


if __name__ == "__main__":
    unittest.main()
