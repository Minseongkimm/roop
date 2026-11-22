# Roop

Local autonomous coding agent engine for MacBook Air M3 (16GB).  
**Phase 6 complete (MVP):** Analyzer → Task Manager → Context Builder → Executor → Verifier/Memory → Night Scheduler.

**Stack:** Python 3.11+ · Ollama on `localhost:11434` · 7–8B local model

## Install

```bash
git clone https://github.com/Minseongkimm/roop.git
cd roop
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ollama pull qwen2.5-coder:7b
```

## Commands

```bash
roop doctor --path /path/to/app
roop analyze /path/to/app

# Task queue
roop enqueue "fix free-message gate" \
  --feature chat --allow-paths ".agent/**" --verify "true" \
  --db /path/to/app/.agent/roop-tasks.sqlite3
roop tasks list --db /path/to/app/.agent/roop-tasks.sqlite3

# Context packet only
roop context 1 --role coder --project /path/to/app \
  --db /path/to/app/.agent/roop-tasks.sqlite3

# Placeholder tick (packet + mark done, no model)
roop tick --project /path/to/app --db /path/to/app/.agent/roop-tasks.sqlite3

# Phase 4–5 dry-run (fake model → harness → verifier → lessons)
roop tick --dry-run --project /path/to/app \
  --db /path/to/app/.agent/roop-tasks.sqlite3

# Live Ollama execute
roop tick --execute --project /path/to/app \
  --db /path/to/app/.agent/roop-tasks.sqlite3

# Phase 6 night drain + report
roop night --dry-run --project /path/to/app \
  --db /path/to/app/.agent/roop-tasks.sqlite3
roop schedule-plist --project /path/to/app --hour 2

pytest
```

## Phase map

| Phase | What |
|------|------|
| 1 | `analyze` → `.agent/` project map |
| 2 | SQLite Task Manager (deps, retries, block) |
| 3 | Context Builder → `.agent/packets/` |
| 4 | Agent Executor (Ollama/dry-run + tools) |
| 5 | Verifier + `.agent/memory/lessons.md` |
| 6 | `night` report + launchd plist template |
| 7 | Round JSONL + hard-stop `wip/` + eval suite/scorecard |

## Eval (Stage 2)

```bash
roop eval list
roop eval enqueue --project /path/to/app --task clamp-util
roop night --project /path/to/app --db .agent/roop-eval.sqlite3
roop eval scorecard --project /path/to/app --db .agent/roop-eval.sqlite3
```

Suite: `evals/v1/manifest.json` (10 easy + 10 medium).

## Safety

- Writes: `.agent/**` plus task `allow_paths`
- Model claims are not truth — Verifier uses exit codes / patch fences
- Identical SAW twice or max retries → `blocked`
- `schedule-plist` writes a template only; does not `launchctl load`

## Layout

```text
src/roop/
  analyze/          # Phase 1
  orchestrator/     # Phase 2 + tick loop
  context/          # Phase 3
  executor/         # Phase 4
  verifier/         # Phase 5
  memory/           # Phase 5 lessons
  scheduler/        # Phase 6
  harness/          # WriteGuard + tools
  adapters/         # Ollama
```
