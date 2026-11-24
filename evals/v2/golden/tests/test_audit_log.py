import unittest

from src.api import create_item, delete_item, list_audit
from src.audit import AuditLog
from src.service import InventoryService


class TestAuditLog(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = AuditLog()
        self.service = InventoryService(audit=self.audit)

    def test_records_create_delete_adjust_only_on_success(self) -> None:
        item = self.service.create_item("A-1", "Alpha", 5, 100)
        self.service.adjust_stock(item.id, -2)
        with self.assertRaises(ValueError):
            self.service.adjust_stock(item.id, -10)
        self.service.delete_item(item.id)
        with self.assertRaises(KeyError):
            self.service.delete_item(item.id)
        events = self.audit.events()
        self.assertEqual([event["action"] for event in events], ["create", "adjust", "delete"])
        self.assertEqual(events[0]["id"], 1)
        self.assertEqual(events[0]["item_id"], item.id)
        self.assertEqual(events[0]["sku"], "A-1")
        self.assertEqual(events[1]["delta"], -2)
        self.assertEqual(events[2]["item_id"], item.id)

    def test_events_are_copied(self) -> None:
        self.service.create_item("A-1", "Alpha", 1, 100)
        events = self.audit.events()
        events[0]["action"] = "tampered"
        self.assertEqual(self.audit.events()[0]["action"], "create")

    def test_api_lists_events(self) -> None:
        created = create_item(
            self.service,
            {"sku": "B-2", "name": "Beta", "quantity": 1, "price_cents": 50},
        )
        self.assertTrue(created["ok"])
        listed = list_audit(self.service)
        self.assertTrue(listed["ok"])
        self.assertEqual(listed["events"][0]["action"], "create")
        missing = delete_item(self.service, 999)
        self.assertFalse(missing["ok"])
        self.assertEqual(len(list_audit(self.service)["events"]), 1)


if __name__ == "__main__":
    unittest.main()
