import unittest
from src.inventory import Inventory
from src.sku import normalize_sku


class TestInventory(unittest.TestCase):
    def test_stock(self) -> None:
        self.assertEqual(normalize_sku(" ab-12 "), "AB-12")
        stock = Inventory()
        stock.add("ab-12", 2)
        self.assertEqual(stock.count("AB-12"), 2)
        with self.assertRaises(ValueError):
            stock.remove("ab-12", 3)
        self.assertEqual(stock.count("ab-12"), 2)
        stock.remove("ab-12", 2)
        self.assertEqual(stock.count("missing-1"), 0)

    def test_invalid(self) -> None:
        for text in ("-AB", "A--B", "A-", ""):
            with self.assertRaises(ValueError):
                normalize_sku(text)
        with self.assertRaises(ValueError):
            Inventory().add("A", True)
        with self.assertRaises(ValueError):
            Inventory().add("A", 0)


if __name__ == "__main__":
    unittest.main()
