import unittest

from src.api import delete_item, get_item, list_items, restore_item
from src.service import InventoryService


class TestSoftDelete(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InventoryService()
        self.keep = self.service.create_item("A-1", "Keep", 1, 100)
        self.gone = self.service.create_item("B-2", "Gone", 2, 200)

    def test_delete_hides_item_but_keeps_id(self) -> None:
        self.service.delete_item(self.gone.id)
        with self.assertRaises(KeyError):
            self.service.get_item(self.gone.id)
        hidden = self.service.get_item(self.gone.id, include_deleted=True)
        self.assertTrue(hidden.deleted)
        self.assertEqual(hidden.id, self.gone.id)
        self.assertEqual(
            [item.id for item in self.service.list_items()],
            [self.keep.id],
        )
        listed = self.service.list_items(include_deleted=True)
        self.assertEqual([item.id for item in listed], [self.keep.id, self.gone.id])
        next_item = self.service.create_item("C-3", "New", 1, 1)
        self.assertNotEqual(next_item.id, self.gone.id)

    def test_restore_and_error_cases(self) -> None:
        self.service.delete_item(self.gone.id)
        restored = self.service.restore_item(self.gone.id)
        self.assertFalse(restored.deleted)
        self.assertEqual(self.service.get_item(self.gone.id).name, "Gone")
        with self.assertRaises(ValueError):
            self.service.restore_item(self.gone.id)
        with self.assertRaises(KeyError):
            self.service.restore_item(999)
        with self.assertRaises(KeyError):
            self.service.delete_item(999)
        self.service.delete_item(self.gone.id)
        with self.assertRaises(KeyError):
            self.service.delete_item(self.gone.id)

    def test_api_restore_and_filters(self) -> None:
        self.assertTrue(delete_item(self.service, self.gone.id)["ok"])
        self.assertEqual(get_item(self.service, self.gone.id)["error"], "not found")
        hidden = list_items(self.service, {})
        self.assertEqual([item["id"] for item in hidden["items"]], [self.keep.id])
        shown = list_items(self.service, {"include_deleted": "true"})
        self.assertEqual(
            [item["id"] for item in shown["items"]],
            [self.keep.id, self.gone.id],
        )
        self.assertTrue(shown["items"][1]["deleted"])
        restored = restore_item(self.service, self.gone.id)
        self.assertTrue(restored["ok"])
        self.assertFalse(restored["item"]["deleted"])
        already = restore_item(self.service, self.gone.id)
        self.assertFalse(already["ok"])


if __name__ == "__main__":
    unittest.main()
