#!/usr/bin/env bash
# ============================================================
# 在 Linux 上打包为单文件可执行程序
# 用法: ./packaging/build-linux.sh
# 产物: dist/BiliStreamRecorder
# ============================================================
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"

if [ ! -x "$PY" ]; then
    echo "未找到虚拟环境 venv，请先执行："
    echo "  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt pyinstaller"
    exit 1
fi

cd "$ROOT"
"$PY" -m PyInstaller \
    --noconfirm --clean --onefile \
    --name "BiliStreamRecorder" \
    --collect-all bilibili_api \
    --collect-all streamlink \
    --collect-all httpx \
    --collect-all certifi \
    app.py

echo "打包完成: $ROOT/dist/BiliStreamRecorder"
