import unittest
from src.email_domain import same_domain
from src.email_split import split_email


class TestEmailDomain(unittest.TestCase):
    def test_split(self) -> None:
        self.assertEqual(split_email("A@B.COM"), ("a", "b.com"))
        self.assertTrue(same_domain("a@x.com", "B@X.com"))
        self.assertFalse(same_domain("a@x.com", "b@y.com"))

    def test_invalid(self) -> None:
        for text in ("nodomain", "a@b", "a@@b.com", "@x.com", "a@"):
            with self.assertRaises(ValueError):
                split_email(text)


if __name__ == "__main__":
    unittest.main()
