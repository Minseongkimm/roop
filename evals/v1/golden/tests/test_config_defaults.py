import tempfile
import unittest
from pathlib import Path

from src.config_io import load_config, save_config
from src.defaults import apply_defaults


class TestConfigIo(unittest.TestCase):
    def test_roundtrip_and_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "c.json"
            save_config(str(path), {"a": 1})
            self.assertEqual(load_config(str(path)), {"a": 1})
            path.write_text("[", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(str(path))
            missing = Path(tmp) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                load_config(str(missing))

    def test_save_rejects_non_dict(self) -> None:
        with self.assertRaises(TypeError):
            save_config("x.json", [1])


class TestDefaults(unittest.TestCase):
    def test_nested_merge_does_not_share_state(self) -> None:
        data = {"db": {"host": "local"}, "n": 1}
        defaults = {"db": {"host": "other", "port": 5}, "n": 9, "extra": {"a": 1}}
        merged = apply_defaults(data, defaults)
        self.assertEqual(
            merged,
            {"db": {"host": "local", "port": 5}, "n": 1, "extra": {"a": 1}},
        )
        self.assertEqual(data, {"db": {"host": "local"}, "n": 1})
        merged["extra"]["a"] = 2
        self.assertEqual(defaults["extra"]["a"], 1)

    def test_lists_are_replaced(self) -> None:
        self.assertEqual(
            apply_defaults({"a": [1]}, {"a": [1, 2], "b": [3]}),
            {"a": [1], "b": [3]},
        )
        with self.assertRaises(TypeError):
            apply_defaults([], {})


if __name__ == "__main__":
    unittest.main()
