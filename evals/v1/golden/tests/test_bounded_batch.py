import unittest

from src.batch import drain
from src.bqueue import BoundedQueue


class TestBoundedQueue(unittest.TestCase):
    def test_fifo_and_full(self) -> None:
        queue = BoundedQueue(2)
        queue.push("a")
        queue.push("b")
        self.assertTrue(queue.is_full())
        with self.assertRaises(OverflowError):
            queue.push("c")
        self.assertEqual(queue.peek(), "a")
        self.assertEqual(queue.pop(), "a")
        self.assertEqual(queue.size(), 1)
        self.assertFalse(queue.is_empty())

    def test_push_many_is_atomic(self) -> None:
        queue = BoundedQueue(2)
        queue.push("a")
        with self.assertRaises(OverflowError):
            queue.push_many(["b", "c"])
        self.assertEqual(queue.pop(), "a")
        self.assertTrue(queue.is_empty())

    def test_invalid_and_empty(self) -> None:
        with self.assertRaises(ValueError):
            BoundedQueue(0)
        queue = BoundedQueue(1)
        with self.assertRaises(IndexError):
            queue.pop()
        with self.assertRaises(IndexError):
            queue.peek()


class TestDrain(unittest.TestCase):
    def test_drain_limit(self) -> None:
        queue = BoundedQueue(4)
        queue.push_many([1, 2, 3])
        self.assertEqual(drain(queue, 2), [1, 2])
        self.assertEqual(drain(queue, 5), [3])
        self.assertEqual(drain(queue, 1), [])
        with self.assertRaises(ValueError):
            drain(queue, 0)


if __name__ == "__main__":
    unittest.main()
