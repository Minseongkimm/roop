import unittest

from src.store import Store


class TestItemSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Store()
        self.a = self.store.create_item("WDG-1", "Blue Widget", 1, 100)
        self.b = self.store.create_item("WDG-2", "Red Gadget", 2, 200)
        self.c = self.store.create_item("BOLT-9", "Widget Bolt", 3, 50)

    def test_matches_name_or_sku_case_insensitive(self) -> None:
        by_name = self.store.search("widget")
        self.assertEqual([item.id for item in by_name], [self.a.id, self.c.id])
        by_sku = self.store.search("wDg")
        self.assertEqual([item.id for item in by_sku], [self.a.id, self.b.id])
        exact = self.store.search("BOLT-9")
        self.assertEqual([item.id for item in exact], [self.c.id])

    def test_no_match_and_invalid_query(self) -> None:
        self.assertEqual(self.store.search("missing"), [])
        for query in ("", "   ", "\t"):
            with self.assertRaises(ValueError) as ctx:
                self.store.search(query)
            self.assertEqual(str(ctx.exception), "invalid query")
        with self.assertRaises(ValueError):
            self.store.search(None)  # type: ignore[arg-type]

    def test_results_are_sorted_and_do_not_mutate(self) -> None:
        before = [item.id for item in self.store.list_items()]
        found = self.store.search("wdg")
        self.assertEqual([item.id for item in found], [self.a.id, self.b.id])
        self.assertEqual([item.id for item in self.store.list_items()], before)


if __name__ == "__main__":
    unittest.main()
