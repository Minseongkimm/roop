# Roop MAP

- `src/roop/` — 엔진 (analyze, tasks, context, executor, verifier, night, eval, telemetry)
- `src/roop/engines/` — 공통 엔진 인터페이스, Best-of-5 하네스, Roop/Aider 어댑터
- `evals/v1/` — 평가 매니페스트 + `golden/tests` 고정 테스트. `split`은 practice / heldout
- `tests/` — Roop 자체 단위 테스트
- `docs/` — MAP / PROGRESS / HISTORY / CURSOR_BUDGET
- `.agent/` (타깃 프로젝트) — packets, runs JSONL, reports, sqlite

실행: `.venv/bin/python -m roop.cli …`  
자주 씀: `analyze`, `enqueue`, `tick --execute`, `night`, `eval enqueue|scorecard`  
체크: `make check` (= 실패만 요약하는 pytest)  
실패 모음: `python scripts/collect_failures.py --db PATH --out FAILURES.md`
