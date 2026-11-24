import tempfile
import unittest
from pathlib import Path

from src.config import DEFAULTS, load_config


class TestConfigParser(unittest.TestCase):
    def _write(self, text: str) -> str:
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".conf", delete=False
        )
        handle.write(text)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_missing_file_raises(self) -> None:
        missing = Path(tempfile.gettempdir()) / "roop-v2-missing-config.conf"
        if missing.exists():
            missing.unlink()
        with self.assertRaises(FileNotFoundError):
            load_config(str(missing))

    def test_empty_and_comments_use_defaults_without_sharing_state(self) -> None:
        path = self._write("\n# just a comment\n")
        loaded = load_config(path)
        self.assertEqual(loaded, DEFAULTS)
        self.assertIsNot(loaded, DEFAULTS)
        loaded["currency"] = "KRW"
        self.assertEqual(DEFAULTS["currency"], "USD")
        again = load_config(path)
        self.assertEqual(again["currency"], "USD")

    def test_overrides_types_and_spaces(self) -> None:
        path = self._write(
            "low_stock_threshold = 0\n"
            "currency = KRW\n"
            "page_size=50\n"
        )
        loaded = load_config(path)
        self.assertEqual(
            loaded,
            {"low_stock_threshold": 0, "currency": "KRW", "page_size": 50},
        )
        self.assertIsInstance(loaded["low_stock_threshold"], int)
        self.assertIsInstance(loaded["page_size"], int)

    def test_rejects_unknown_duplicate_and_invalid(self) -> None:
        with self.assertRaises(ValueError):
            load_config(self._write("unknown = 1\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("page_size = 1\npage_size = 2\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("not-a-line\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("page_size = 0\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("page_size = -1\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("low_stock_threshold = -1\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("currency =\n"))
        with self.assertRaises(ValueError):
            load_config(self._write("page_size = 1.5\n"))


if __name__ == "__main__":
    unittest.main()
