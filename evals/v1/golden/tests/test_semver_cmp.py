import unittest
from src.semver import parse_semver
from src.version_cmp import compare_semver


class TestSemver(unittest.TestCase):
    def test_parse_and_compare(self) -> None:
        self.assertEqual(parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("01.2.3"), (1, 2, 3))
        self.assertEqual(compare_semver("1.0.0", "1.0.1"), -1)
        self.assertEqual(compare_semver("1.2.3", "1.2.3"), 0)
        self.assertEqual(compare_semver("2.0.0", "1.9.9"), 1)

    def test_invalid(self) -> None:
        for text in ("1.2", "1.2.3.4", "a.b.c", "", "1.-1.0"):
            with self.assertRaises(ValueError):
                parse_semver(text)


if __name__ == "__main__":
    unittest.main()
