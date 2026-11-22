import unittest
from src.email_mask import mask_email


class TestMaskEmail(unittest.TestCase):
    def test_mask(self) -> None:
        self.assertEqual(mask_email("abcd@x.com"), "a***@x.com")
        self.assertEqual(mask_email("ab@x.com"), "a*@x.com")
        self.assertEqual(mask_email("a@x.com"), "a*@x.com")

    def test_invalid(self) -> None:
        for text in ("abc", "a@@x.com", "@x.com", "a@"):
            with self.assertRaises(ValueError):
                mask_email(text)


if __name__ == "__main__":
    unittest.main()
