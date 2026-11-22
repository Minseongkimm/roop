import unittest
from src.clock import add_minutes
from src.duration import parse_duration


class TestDurationClock(unittest.TestCase):
    def test_duration(self) -> None:
        self.assertEqual(parse_duration("90"), 90)
        self.assertEqual(parse_duration("1h"), 60)
        self.assertEqual(parse_duration("1h30m"), 90)
        self.assertEqual(parse_duration("45m"), 45)
        self.assertEqual(parse_duration("2h"), 120)

    def test_duration_invalid(self) -> None:
        for text in ("", "1x", "-1", "1h30", "h"):
            with self.assertRaises(ValueError):
                parse_duration(text)

    def test_clock(self) -> None:
        self.assertEqual(add_minutes("23:30", "1h"), "00:30")
        self.assertEqual(add_minutes("00:00", "45m"), "00:45")
        with self.assertRaises(ValueError):
            add_minutes("24:00", "1")
        with self.assertRaises(ValueError):
            add_minutes("12:60", "1")


if __name__ == "__main__":
    unittest.main()
