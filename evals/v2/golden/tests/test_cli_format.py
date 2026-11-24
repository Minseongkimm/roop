import io
import json
import unittest

from src.cli import format_table, main
from src.service import InventoryService


class TestCliFormat(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InventoryService()
        self.service.create_item("A-1", "Alpha", 2, 150)
        self.service.create_item("B-2", "Beta", 0, 99)

    def _run(self, argv: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        code = main(argv, service=self.service, stdout=out)
        return code, out.getvalue()

    def test_default_and_table_format(self) -> None:
        expected = format_table(self.service.list_items()) + "\n"
        code, text = self._run(["list"])
        self.assertEqual(code, 0)
        self.assertEqual(text, expected)
        code, text = self._run(["list", "--format", "table"])
        self.assertEqual(code, 0)
        self.assertEqual(text, expected)

    def test_json_format(self) -> None:
        code, text = self._run(["list", "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(text)
        self.assertEqual(
            payload,
            [
                {
                    "id": 1,
                    "sku": "A-1",
                    "name": "Alpha",
                    "quantity": 2,
                    "price_cents": 150,
                },
                {
                    "id": 2,
                    "sku": "B-2",
                    "name": "Beta",
                    "quantity": 0,
                    "price_cents": 99,
                },
            ],
        )

    def test_empty_list_and_invalid_format(self) -> None:
        empty = InventoryService()
        out = io.StringIO()
        code = main(["list", "--format", "json"], service=empty, stdout=out)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue()), [])
        code, _ = self._run(["list", "--format", "yaml"])
        self.assertEqual(code, 2)

    def test_add_and_get_still_work(self) -> None:
        code, text = self._run(
            ["add", "--sku", "C-3", "--name", "Gamma", "--quantity", "1", "--price-cents", "10"]
        )
        self.assertEqual(code, 0)
        self.assertIn("C-3", text)
        code, text = self._run(["get", "1"])
        self.assertEqual(code, 0)
        self.assertIn("Alpha", text)


if __name__ == "__main__":
    unittest.main()
