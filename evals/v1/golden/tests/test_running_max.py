import unittest
from src.running import running_max


class TestRunningMax(unittest.TestCase):
    def test_max(self) -> None:
        source = [1, 3, 2, 5]
        self.assertEqual(running_max(source), [1, 3, 3, 5])
        self.assertEqual(source, [1, 3, 2, 5])
        self.assertEqual(running_max([]), [])
        self.assertEqual(running_max([-2, -5, -1]), [-2, -2, -1])
        self.assertEqual(running_max([0, 0]), [0, 0])


if __name__ == "__main__":
    unittest.main()
