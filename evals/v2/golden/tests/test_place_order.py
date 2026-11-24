import unittest

from src.api import cancel_order, get_order, list_orders, place_order
from src.service import InventoryService


class TestPlaceOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InventoryService()
        self.hammer = self.service.create_item("H-1", "Hammer", 10, 500)
        self.nail = self.service.create_item("N-1", "Nail", 100, 10)

    def test_place_decrements_stock_and_totals(self) -> None:
        order = self.service.place_order(
            [
                {"item_id": self.hammer.id, "quantity": 2},
                {"item_id": self.nail.id, "quantity": 20},
            ]
        )
        self.assertEqual(order.status, "placed")
        self.assertEqual(order.total_cents, 2 * 500 + 20 * 10)
        self.assertEqual(len(order.lines), 2)
        self.assertEqual(self.service.get_item(self.hammer.id).quantity, 8)
        self.assertEqual(self.service.get_item(self.nail.id).quantity, 80)
        self.assertEqual(self.service.get_order(order.id).id, order.id)
        self.assertEqual(len(self.service.list_orders()), 1)

    def test_failures_do_not_change_stock(self) -> None:
        before_h = self.service.get_item(self.hammer.id).quantity
        before_n = self.service.get_item(self.nail.id).quantity
        with self.assertRaises(ValueError):
            self.service.place_order(
                [
                    {"item_id": self.hammer.id, "quantity": 2},
                    {"item_id": self.nail.id, "quantity": 999},
                ]
            )
        self.assertEqual(self.service.get_item(self.hammer.id).quantity, before_h)
        self.assertEqual(self.service.get_item(self.nail.id).quantity, before_n)
        with self.assertRaises(KeyError):
            self.service.place_order([{"item_id": 999, "quantity": 1}])
        self.assertEqual(self.service.get_item(self.hammer.id).quantity, before_h)
        with self.assertRaises(ValueError):
            self.service.place_order([])
        with self.assertRaises(ValueError):
            self.service.place_order([{"item_id": self.hammer.id, "quantity": 0}])
        with self.assertRaises(ValueError):
            self.service.place_order(
                [
                    {"item_id": self.hammer.id, "quantity": 1},
                    {"item_id": self.hammer.id, "quantity": 1},
                ]
            )

    def test_cancel_restores_stock_once(self) -> None:
        order = self.service.place_order(
            [{"item_id": self.hammer.id, "quantity": 3}]
        )
        cancelled = self.service.cancel_order(order.id)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual(self.service.get_item(self.hammer.id).quantity, 10)
        with self.assertRaises(ValueError):
            self.service.cancel_order(order.id)
        self.assertEqual(self.service.get_item(self.hammer.id).quantity, 10)

    def test_api_handlers(self) -> None:
        placed = place_order(
            self.service,
            {"lines": [{"item_id": self.nail.id, "quantity": 5}]},
        )
        self.assertTrue(placed["ok"])
        self.assertEqual(placed["order"]["total_cents"], 50)
        order_id = placed["order"]["id"]
        self.assertTrue(get_order(self.service, order_id)["ok"])
        self.assertEqual(len(list_orders(self.service)["orders"]), 1)
        cancelled = cancel_order(self.service, order_id)
        self.assertTrue(cancelled["ok"])
        self.assertEqual(cancelled["order"]["status"], "cancelled")
        self.assertEqual(self.service.get_item(self.nail.id).quantity, 100)
        again = cancel_order(self.service, order_id)
        self.assertFalse(again["ok"])
        missing = place_order(
            self.service,
            {"lines": [{"item_id": 999, "quantity": 1}]},
        )
        self.assertFalse(missing["ok"])


if __name__ == "__main__":
    unittest.main()
