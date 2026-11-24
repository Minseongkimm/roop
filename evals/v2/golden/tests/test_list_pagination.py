import unittest

from src.api import list_items
from src.service import InventoryService


class TestListPagination(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InventoryService()
        for index in range(45):
            self.service.create_item(
                f"SKU-{index}", f"Item {index}", index, index * 10
            )

    def test_defaults_and_pages(self) -> None:
        first = list_items(self.service, {})
        self.assertTrue(first["ok"])
        self.assertEqual(first["page"], 1)
        self.assertEqual(first["page_size"], 20)
        self.assertEqual(first["total"], 45)
        self.assertEqual(first["total_pages"], 3)
        self.assertEqual(len(first["items"]), 20)
        self.assertEqual(first["items"][0]["id"], 1)
        self.assertEqual(first["items"][-1]["id"], 20)
        third = list_items(self.service, {"page": 3, "page_size": 20})
        self.assertEqual(len(third["items"]), 5)
        self.assertEqual(third["items"][0]["id"], 41)
        self.assertEqual(third["total"], 45)
        self.assertEqual(third["total_pages"], 3)
        empty_page = list_items(self.service, {"page": 9, "page_size": 20})
        self.assertTrue(empty_page["ok"])
        self.assertEqual(empty_page["items"], [])
        self.assertEqual(empty_page["total"], 45)
        self.assertEqual(empty_page["total_pages"], 3)

    def test_page_size_bounds_and_empty_store(self) -> None:
        ok = list_items(self.service, {"page": 1, "page_size": 100})
        self.assertTrue(ok["ok"])
        self.assertEqual(len(ok["items"]), 45)
        for query in (
            {"page": 0},
            {"page": -1},
            {"page_size": 0},
            {"page_size": 101},
            {"page": True},
            {"page_size": "20"},
        ):
            result = list_items(self.service, query)
            self.assertFalse(result["ok"], query)
            self.assertIn("error", result)
        empty = list_items(InventoryService(), {"page": 1, "page_size": 20})
        self.assertTrue(empty["ok"])
        self.assertEqual(empty["items"], [])
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["total_pages"], 0)

    def test_service_paginate_helper(self) -> None:
        items, total = self.service.paginate_items(2, 10)
        self.assertEqual(total, 45)
        self.assertEqual([item.id for item in items], list(range(11, 21)))
        with self.assertRaises(ValueError):
            self.service.paginate_items(0, 10)
        with self.assertRaises(ValueError):
            self.service.paginate_items(1, 101)


if __name__ == "__main__":
    unittest.main()
