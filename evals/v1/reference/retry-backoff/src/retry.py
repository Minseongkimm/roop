"""Call a function again after matching exceptions, with backoff delays."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.backoff import backoff_ms

T = TypeVar("T")


def retry(
    fn: Callable[[], T],
    retries: int,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[int], None] | None = None,
) -> T:
    if retries < 0:
        raise ValueError("retries must be >= 0")
    attempt: int = 0
    while True:
        try:
            return fn()
        except exceptions:
            if attempt >= retries:
                raise
            attempt += 1
            if sleep is not None:
                sleep(backoff_ms(attempt))
