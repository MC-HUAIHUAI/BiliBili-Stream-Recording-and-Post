#!/usr/bin/env bash
# 从源码运行（Linux）。优先用 venv，否则用系统 python3。
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
[ -x "$PY" ] || PY="python3"
exec "$PY" "$ROOT/app.py"
