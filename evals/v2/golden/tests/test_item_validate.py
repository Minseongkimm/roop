import unittest

from src.service import InventoryService


class TestItemValidate(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InventoryService()

    def test_create_normalizes_sku_and_name(self) -> None:
        item = self.service.create_item(" ab-12 ", "  Widget  ", 0, 0)
        self.assertEqual(item.sku, "AB-12")
        self.assertEqual(item.name, "Widget")
        self.assertEqual(item.quantity, 0)
        self.assertEqual(item.price_cents, 0)
        found = self.service.get_item(item.id)
        self.assertEqual(found.sku, "AB-12")

    def test_invalid_sku_rejected(self) -> None:
        for sku in ("", "  ", "-AB", "A--B", "A-", "ab_1", "ab 1"):
            with self.assertRaises(ValueError) as ctx:
                self.service.create_item(sku, "Widget", 1, 100)
            self.assertEqual(str(ctx.exception), "invalid sku")

    def test_duplicate_sku_is_case_insensitive(self) -> None:
        self.service.create_item("ab-12", "Widget", 1, 100)
        with self.assertRaises(ValueError) as ctx:
            self.service.create_item("AB-12", "Other", 1, 100)
        self.assertEqual(str(ctx.exception), "duplicate sku")

    def test_update_duplicate_sku_rejected_same_item_allowed(self) -> None:
        first = self.service.create_item("AA-1", "One", 1, 100)
        self.service.create_item("BB-2", "Two", 1, 100)
        with self.assertRaises(ValueError):
            self.service.update_item(first.id, sku="bb-2")
        updated = self.service.update_item(first.id, sku="aa-1", name="One")
        self.assertEqual(updated.sku, "AA-1")

    def test_invalid_name_and_bounds(self) -> None:
        self.service.create_item("OK-1", "A" * 80, 1, 1)
        for name in ("", "  ", "A" * 81):
            with self.assertRaises(ValueError) as ctx:
                self.service.create_item("OK-2", name, 1, 1)
            self.assertEqual(str(ctx.exception), "invalid name")

    def test_invalid_quantity_and_price(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.service.create_item("OK-3", "N", -1, 1)
        self.assertEqual(str(ctx.exception), "invalid quantity")
        with self.assertRaises(ValueError):
            self.service.create_item("OK-3", "N", True, 1)
        with self.assertRaises(ValueError):
            self.service.create_item("OK-3", "N", 1.5, 1)  # type: ignore[arg-type]
        with self.assertRaises(ValueError) as ctx:
            self.service.create_item("OK-3", "N", 1, -1)
        self.assertEqual(str(ctx.exception), "invalid price")
        with self.assertRaises(ValueError):
            self.service.create_item("OK-3", "N", 1, True)
        item = self.service.create_item("OK-3", "N", 1, 1)
        with self.assertRaises(ValueError):
            self.service.update_item(item.id, quantity=-2)


if __name__ == "__main__":
    unittest.main()
