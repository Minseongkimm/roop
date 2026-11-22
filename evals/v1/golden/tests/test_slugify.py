import unittest
from src.slugify import slugify


class TestSlugify(unittest.TestCase):
    def test_hello_world(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_empty(self) -> None:
        self.assertEqual(slugify(""), "")

    def test_collapse(self) -> None:
        self.assertEqual(slugify("Hello---World!!"), "hello-world")


if __name__ == "__main__":
    unittest.main()
