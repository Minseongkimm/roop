#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi
OUT="$("$PY" -m pytest -q --tb=line 2>&1)" || STATUS=$?
STATUS="${STATUS:-0}"
echo "$OUT" | tail -n 3
if [[ "$STATUS" -ne 0 ]]; then
  echo "--- failures ---"
  echo "$OUT" | rg -n "FAILED|ERROR|E |AssertionError|Error" | head -n 40 || true
  exit "$STATUS"
fi
echo "check ok"
