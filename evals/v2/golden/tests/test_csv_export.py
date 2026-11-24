import unittest

from src.csv_io import export_csv, import_csv
from src.models import Item


class TestCsvExport(unittest.TestCase):
    def test_empty_export_is_header_only(self) -> None:
        self.assertEqual(export_csv([]), "sku,name,quantity,price_cents\n")

    def test_roundtrip_and_quoting(self) -> None:
        items = [
            Item(id=1, sku="A-1", name="Plain", quantity=2, price_cents=150),
            Item(id=2, sku="B-2", name="Has, comma", quantity=0, price_cents=99),
        ]
        text = export_csv(items)
        self.assertTrue(text.startswith("sku,name,quantity,price_cents\n"))
        self.assertIn('"Has, comma"', text)
        rows = import_csv(text)
        self.assertEqual(
            rows,
            [
                {"sku": "A-1", "name": "Plain", "quantity": 2, "price_cents": 150},
                {"sku": "B-2", "name": "Has, comma", "quantity": 0, "price_cents": 99},
            ],
        )
        self.assertIsInstance(rows[0]["quantity"], int)
        self.assertIsInstance(rows[0]["price_cents"], int)

    def test_import_rejects_bad_input(self) -> None:
        with self.assertRaises(ValueError):
            import_csv("")
        with self.assertRaises(ValueError):
            import_csv("sku,name,qty,price_cents\n")
        with self.assertRaises(ValueError):
            import_csv("sku,name,quantity,price_cents\nA-1,OnlyThree,1\n")
        with self.assertRaises(ValueError):
            import_csv("sku,name,quantity,price_cents\n,Name,1,2\n")
        with self.assertRaises(ValueError):
            import_csv("sku,name,quantity,price_cents\nA-1,,1,2\n")
        with self.assertRaises(ValueError):
            import_csv("sku,name,quantity,price_cents\nA-1,Name,x,2\n")
        rows = import_csv("sku,name,quantity,price_cents\nA-1,Name,-3,2\n")
        self.assertEqual(rows[0]["quantity"], -3)


if __name__ == "__main__":
    unittest.main()
