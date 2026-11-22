"""Caps for independent Best-of-5 samples.

The orchestrator can repair one local attempt up to ``DEFAULT_MAX_RETRIES`` (4).
Best-of-5 does not multiply that loop: each sample is one engine generation,
and a task stops at the first sample whose tests pass.
"""

from __future__ import annotations

BEST_OF_N: int = 5
BEST_OF_TEMPERATURES: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8)
MAX_GENERATIONS_PER_TASK: int = BEST_OF_N
MAX_SECONDS_PER_TASK: float = 600.0
MAX_SECONDS_PER_GENERATION: float = 240.0
