import unittest

from src.backoff import backoff_ms
from src.retry import retry


class TestBackoff(unittest.TestCase):
    def test_sequence(self) -> None:
        self.assertEqual(backoff_ms(1), 100)
        self.assertEqual(backoff_ms(1, base_ms=10), 10)
        self.assertEqual(backoff_ms(3, base_ms=10), 40)

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            backoff_ms(0)
        with self.assertRaises(ValueError):
            backoff_ms(1, base_ms=-1)


class TestRetry(unittest.TestCase):
    def test_success_after_retries(self) -> None:
        calls = {"n": 0}
        delays: list[int] = []

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("nope")
            return "ok"

        result = retry(flaky, retries=2, exceptions=(RuntimeError,), sleep=delays.append)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(delays, [100, 200])

    def test_exhausted_and_unrelated(self) -> None:
        delays: list[int] = []

        def always() -> None:
            raise RuntimeError("nope")

        with self.assertRaises(RuntimeError):
            retry(always, retries=1, exceptions=(RuntimeError,), sleep=lambda _ms: None)

        def wrong() -> None:
            raise ValueError("bad")

        with self.assertRaises(ValueError):
            retry(wrong, retries=3, exceptions=(RuntimeError,), sleep=delays.append)
        self.assertEqual(delays, [])

    def test_negative_retries(self) -> None:
        with self.assertRaises(ValueError):
            retry(lambda: 1, retries=-1)


if __name__ == "__main__":
    unittest.main()
