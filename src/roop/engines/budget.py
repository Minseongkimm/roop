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
# Whole-file rewrites of several sources do not finish in 240s on a local 7B.
MAX_SECONDS_PER_MULTIFILE_GENERATION: float = 600.0
# Overnight run: one task gets this many attempts, each attempt dies at this
# many seconds, and the whole run stops starting tasks after this many dollars.
MAX_ATTEMPTS_PER_TASK: int = 3
MAX_SECONDS_PER_ATTEMPT: float = 600.0
MAX_USD_PER_RUN: float = 5.0
