import unittest

from src.api import (
    create_category,
    create_item,
    delete_category,
    get_category,
    list_categories,
    update_category,
    update_item,
)
from src.models import Category
from src.service import InventoryService


class TestCategoryCrud(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InventoryService()

    def test_create_get_list_and_slugify(self) -> None:
        tools = self.service.create_category("Tools")
        self.assertIsInstance(tools, Category)
        self.assertEqual(tools.name, "Tools")
        self.assertEqual(tools.slug, "tools")
        explicit = self.service.create_category("Power Tools", slug="power-tools")
        self.assertEqual(explicit.slug, "power-tools")
        self.assertEqual(
            [item.slug for item in self.service.list_categories()],
            ["tools", "power-tools"],
        )
        self.assertEqual(self.service.get_category(tools.id).name, "Tools")

    def test_validation_and_unique_slug(self) -> None:
        self.service.create_category("Tools", slug="tools")
        with self.assertRaises(ValueError):
            self.service.create_category("Other", slug="tools")
        with self.assertRaises(ValueError):
            self.service.create_category("", slug="x")
        with self.assertRaises(ValueError):
            self.service.create_category("A" * 41, slug="long")
        with self.assertRaises(ValueError):
            self.service.create_category("Ok", slug="Bad Slug")
        with self.assertRaises(ValueError):
            self.service.create_category("Ok", slug="-bad")

    def test_update_and_in_use_delete(self) -> None:
        tools = self.service.create_category("Tools")
        parts = self.service.create_category("Parts")
        updated = self.service.update_category(tools.id, name="Hand Tools")
        self.assertEqual(updated.name, "Hand Tools")
        self.assertEqual(updated.slug, "tools")
        with self.assertRaises(ValueError):
            self.service.update_category(tools.id, slug="parts")
        item = self.service.create_item("A-1", "Hammer", 1, 100, category_id=tools.id)
        self.assertEqual(item.category_id, tools.id)
        moved = self.service.update_item(item.id, category_id=parts.id)
        self.assertEqual(moved.category_id, parts.id)
        self.service.delete_category(tools.id)
        with self.assertRaises(ValueError) as ctx:
            self.service.delete_category(parts.id)
        self.assertEqual(str(ctx.exception), "category in use")
        cleared = self.service.update_item(item.id, category_id=None)
        self.assertIsNone(cleared.category_id)
        self.service.delete_category(parts.id)
        with self.assertRaises(KeyError):
            self.service.get_category(parts.id)
        with self.assertRaises(KeyError):
            self.service.create_item("B-2", "Nail", 1, 10, category_id=parts.id)

    def test_api_handlers(self) -> None:
        created = create_category(self.service, {"name": "Cables"})
        self.assertTrue(created["ok"])
        self.assertEqual(created["category"]["slug"], "cables")
        category_id = created["category"]["id"]
        self.assertTrue(get_category(self.service, category_id)["ok"])
        listed = list_categories(self.service)
        self.assertEqual(len(listed["categories"]), 1)
        renamed = update_category(self.service, category_id, {"name": "Wire"})
        self.assertEqual(renamed["category"]["name"], "Wire")
        item = create_item(
            self.service,
            {
                "sku": "C-1",
                "name": "USB",
                "quantity": 1,
                "price_cents": 50,
                "category_id": category_id,
            },
        )
        self.assertEqual(item["item"]["category_id"], category_id)
        blocked = delete_category(self.service, category_id)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "category in use")
        update_item(self.service, item["item"]["id"], {"category_id": None})
        self.assertTrue(delete_category(self.service, category_id)["ok"])
        self.assertEqual(get_category(self.service, category_id)["error"], "not found")


if __name__ == "__main__":
    unittest.main()
