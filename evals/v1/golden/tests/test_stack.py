import unittest
from src.stack import Stack


class TestStack(unittest.TestCase):
    def test_push_pop(self) -> None:
        stack = Stack()
        stack.push(1)
        stack.push(2)
        self.assertEqual(stack.pop(), 2)
        self.assertEqual(stack.pop(), 1)

    def test_peek(self) -> None:
        stack = Stack()
        stack.push("a")
        self.assertEqual(stack.peek(), "a")
        self.assertEqual(stack.size(), 1)

    def test_is_empty(self) -> None:
        stack = Stack()
        self.assertTrue(stack.is_empty())
        stack.push(1)
        self.assertFalse(stack.is_empty())

    def test_empty_errors(self) -> None:
        stack = Stack()
        with self.assertRaises(IndexError):
            stack.pop()
        with self.assertRaises(IndexError):
            stack.peek()


if __name__ == "__main__":
    unittest.main()
