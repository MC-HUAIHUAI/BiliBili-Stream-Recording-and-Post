#!/usr/bin/env bash
# ============================================================
# 在 Ubuntu 22.04 容器内构建 Linux 单文件可执行程序
# 用法（宿主机 / Windows）:
#   docker run --rm -v "E:\stream_record:/src" ubuntu:22.04 \
#       bash /src/packaging/build-linux-docker.sh
# 产物: dist-linux/BiliStreamRecorder
# ============================================================
set -e

export DEBIAN_FRONTEND=noninteractive

# 使用国内 apt 镜像（如需海外可注释掉）
if [ -f /etc/apt/sources.list ]; then
    sed -i 's@http://archive.ubuntu.com/ubuntu@http://mirrors.tuna.tsinghua.edu.cn/ubuntu@g; s@http://security.ubuntu.com/ubuntu@http://mirrors.tuna.tsinghua.edu.cn/ubuntu@g' /etc/apt/sources.list
fi

apt-get update
apt-get install -y --no-install-recommends python3 python3-venv python3-tk ca-certificates binutils libpython3.10

SRC="${SRC:-/src}"
BUILD="${BUILD:-/build}"

rm -rf "$BUILD"
mkdir -p "$BUILD/src/assets"
cp "$SRC"/*.py "$SRC"/requirements.txt "$BUILD/src/"
cp "$SRC"/assets/icon.ico "$BUILD/src/assets/" 2>/dev/null || true

cd "$BUILD/src"
python3 -m venv "$BUILD/venv"
"$BUILD/venv/bin/pip" install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
"$BUILD/venv/bin/pip" install -r requirements.txt pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple

"$BUILD/venv/bin/python" -m PyInstaller \
    --noconfirm --clean --onefile \
    --name BiliStreamRecorder \
    --collect-all bilibili_api \
    --collect-all streamlink \
    --collect-all httpx \
    --collect-all certifi \
    app.py

mkdir -p "$SRC/dist-linux"
cp dist/BiliStreamRecorder "$SRC/dist-linux/BiliStreamRecorder"
chmod +x "$SRC/dist-linux/BiliStreamRecorder" 2>/dev/null || true
echo "OK: $SRC/dist-linux/BiliStreamRecorder"
