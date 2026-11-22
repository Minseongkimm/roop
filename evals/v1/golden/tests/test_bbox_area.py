import unittest
from src.bbox import parse_point
from src.bbox_area import area


class TestBBox(unittest.TestCase):
    def test_area(self) -> None:
        self.assertEqual(parse_point("1, 2"), (1, 2))
        self.assertEqual(parse_point("-1,0"), (-1, 0))
        self.assertEqual(area(["0,0", "2,3"]), 6)
        self.assertEqual(area(["1,1"]), 0)

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            parse_point("1")
        with self.assertRaises(ValueError):
            area([])


if __name__ == "__main__":
    unittest.main()
