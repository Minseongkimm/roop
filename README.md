# Roop

Local autonomous coding agent engine for MacBook Air M3 (16GB).  
Python + Ollama. One local model, sequential roles. Writes only under `<project>/.agent/` until later phases.

## Install (Mac)

```bash
brew install git ripgrep
# Ollama: https://ollama.com — then:
ollama pull qwen2.5-coder:7b   # or another 7–8B Q4-class model

cd roop
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
roop doctor
```

## CLI

```bash
roop doctor
roop analyze /path/to/project   # scaffold .agent/ only
roop enqueue /path/to/project "fix login redirect"
roop tick /path/to/project      # one orchestrator tick (stub)
roop version
```

## Phase 0 status

Implemented: CLI, Ollama adapter, FS write guard, SQLite task stub, analyze skeleton.  
Not yet: full Context Builder, real Coder tools, Verifier loop, night scheduler.
