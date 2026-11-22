import unittest

from src.ledger import Ledger
from src.money import format_cents, parse_cents


class TestMoney(unittest.TestCase):
    def test_parse_and_format(self) -> None:
        self.assertEqual(parse_cents("1"), 100)
        self.assertEqual(parse_cents("1.2"), 120)
        self.assertEqual(parse_cents("$1.20"), 120)
        self.assertEqual(parse_cents("  .5 "), 50)
        self.assertEqual(parse_cents("-0.05"), -5)
        self.assertEqual(format_cents(120), "1.20")
        self.assertEqual(format_cents(-5), "-0.05")
        self.assertEqual(format_cents(0), "0.00")

    def test_parse_invalid(self) -> None:
        for text in ("", "1.234", "abc", "$", "1.", "1,000"):
            with self.assertRaises(ValueError):
                parse_cents(text)


class TestLedger(unittest.TestCase):
    def test_transfer_and_missing(self) -> None:
        ledger = Ledger()
        ledger.deposit("a", 500)
        ledger.transfer("a", "b", 200)
        self.assertEqual(ledger.balance("a"), 300)
        self.assertEqual(ledger.balance("b"), 200)
        self.assertEqual(ledger.balance("missing"), 0)

    def test_rejections_do_not_mutate(self) -> None:
        ledger = Ledger()
        ledger.deposit("a", 100)
        with self.assertRaises(ValueError):
            ledger.withdraw("a", 150)
        with self.assertRaises(ValueError):
            ledger.transfer("a", "b", 0)
        with self.assertRaises(ValueError):
            ledger.transfer("a", "a", 10)
        with self.assertRaises(ValueError):
            ledger.deposit("", 10)
        self.assertEqual(ledger.balance("a"), 100)
        self.assertEqual(ledger.balance("b"), 0)


if __name__ == "__main__":
    unittest.main()
