# Roop

Local autonomous coding agent engine for MacBook Air M3 (16GB).  
Phase 0 scaffold: CLI shell, Ollama adapter, SQLite task queue stub, and a write guard that only allows `<target>/.agent/**`.

**Stack:** Python 3.11+ · Ollama on `localhost:11434` · 7–8B local model

## Mac M3 setup

```bash
# tools
xcode-select --install   # if needed
brew install git ripgrep jq ollama

# model server (one 7–8B Q4 model — do not load two large models)
ollama serve
ollama pull qwen2.5-coder:7b
# or: ollama pull llama3.1:8b
curl -s http://127.0.0.1:11434/api/tags | jq .

# optional memory guardrail
export OLLAMA_CONTEXT_LENGTH=32768
```

## Install

```bash
git clone https://github.com/Minseongkimm/roop.git
cd roop
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands that work (Phase 0)

```bash
roop doctor
roop doctor --path /path/to/your-app
roop analyze /path/to/your-app
roop enqueue "demo task" --db /path/to/your-app/.agent/roop-tasks.sqlite3
roop tick --db /path/to/your-app/.agent/roop-tasks.sqlite3
pytest
```

- `doctor` — checks `git`, `rg`, Ollama `/api/tags`, and optional target git repo
- `analyze` — stub that detects stack markers and writes a minimal `.agent/` tree (no source edits)
- `enqueue` / `tick` — SQLite queue helpers for the sequential orchestrator stub

## Safety defaults

- Writes allowed only under `<target>/.agent/**`
- Source, lockfiles, and configs are read-only in Phase 0
- No worktree/branch creation yet
- Cloud API lane is off by default

## Loop visualizer

Interactive walkthrough of one orchestrator tick cycle:

```bash
cd web && python3 -m http.server 8765 --bind 127.0.0.1
# open http://127.0.0.1:8765
```

## Layout

```text
web/                     # loop visualizer (static site)
src/roop/
  cli.py                 # typer entrypoint
  doctor.py
  adapters/
    model.py             # ModelAdapter protocol
    ollama.py            # HTTP client → :11434
  harness/
    fs_guard.py          # .agent/** write fence
  orchestrator/
    tasks.py             # SQLite CRUD
    loop.py              # single sequential tick stub
  analyze/
    stub.py              # Phase 0 analyze scaffold
tests/
```

## Design notes

Small local models win through orchestration, not raw IQ: one role per tick, short JSON outputs, narrow tools, and a code Verifier. See Project docs for Phase 1+.
