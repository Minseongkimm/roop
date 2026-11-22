import unittest
from src.drop_none import drop_none


class TestDropNone(unittest.TestCase):
    def test_drop(self) -> None:
        source = [0, None, "", False, None]
        self.assertEqual(drop_none(source), [0, "", False])
        self.assertEqual(source, [0, None, "", False, None])
        self.assertEqual(drop_none([]), [])


if __name__ == "__main__":
    unittest.main()
