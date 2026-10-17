# Linux 安装指南

`B站直播录播 + 自动投稿` 基于 Python + tkinter，可在 Linux 上运行。
共 **3 种方式**，任选其一。

> 想了解怎么用？请看 [使用教程](USAGE.md)。Windows 用户请看 [Windows 安装指南](INSTALL-Windows.md)。

---

## 方式零：下载预编译二进制（最省事）

Releases 中提供了 Linux x86_64 单文件：`BiliStreamRecorder`（约 42MB）。

```bash
# 下载后赋予执行权限并运行
chmod +x BiliStreamRecorder
./BiliStreamRecorder
```

**运行环境要求**：
- x86_64 Linux，**glibc ≥ 2.35**（Ubuntu 22.04+ / Debian 12+ / Fedora 36+ 等）
- 桌面环境所需的 X11 运行库（绝大多数桌面发行版已自带）：
  `libx11-6 libxft2 libfontconfig1 libfreetype6`
- 需要图形界面（X11/Wayland），无头服务器请勿用此方式。

> 若你的系统较旧（如 Ubuntu 20.04 / CentOS 7，glibc < 2.35），请使用下面的**方式一（源码）**。

---

## 方式一：从源码运行（兼容性最好）

适合：绝大多数 Linux 用户，最简单、可随时更新。

### 1. 安装系统依赖

程序界面用 tkinter，需要系统自带的 tk 支持（streamlink 直接写流，**不强制需要 ffmpeg**）。

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y python3 python3-venv python3-tk

# Fedora / RHEL
sudo dnf install -y python3 python3-tkinter

# Arch / Manjaro
sudo pacman -S --needed python tk
```

### 2. 获取源码并安装 Python 依赖

```bash
git clone https://github.com/MC-HUAIHUAI/BiliBili-Stream-Recording-and-Post.git
cd BiliBili-Stream-Recording-and-Post

python3 -m venv venv
./venv/bin/pip install -U pip
./venv/bin/pip install -r requirements.txt
# 国内网络可加镜像： -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 运行

```bash
./venv/bin/python app.py
```

或使用附带的脚本：

```bash
chmod +x packaging/run-linux.sh
./packaging/run-linux.sh
```

---

## 方式二：打包成单文件可执行程序

适合：不想装 Python 依赖、想做成绿色可执行文件的用户。

```bash
./venv/bin/pip install pyinstaller
chmod +x packaging/build-linux.sh
./packaging/build-linux.sh
# 产物: dist/BiliStreamRecorder（Linux 可执行文件）
```

运行：

```bash
./dist/BiliStreamRecorder
```

> 说明：Linux 下 PyInstaller 只能在 Linux 上打包（不能交叉编译）。
> 打包机的 glibc 版本要 ≤ 目标机，建议在较旧的发行版上打包以获得更好兼容性。

### 用 Docker 在任意系统上构建（含 Windows / macOS）

如果你的电脑没有 Linux，也可以借助 Docker 构建（已内置国内镜像与依赖安装）：

```bash
# 方式 A：用官方/镜像的 ubuntu:22.04
docker run --rm -v "$PWD:/src" ubuntu:22.04 bash /src/packaging/build-linux-docker.sh

# 方式 B：国内拉不到镜像时，用镜像站前缀
docker run --rm -v "$PWD:/src" docker.m.daocloud.io/library/ubuntu:22.04 \
    bash /src/packaging/build-linux-docker.sh
```

产物：`dist-linux/BiliStreamRecorder`。

> Windows 下把 `$PWD` 换成 `%cd%` 或 `E:\你的路径` 的 PowerShell 写法：
> `docker run --rm -v "E:\stream_record:/src" docker.m.daocloud.io/library/ubuntu:22.04 bash /src/packaging/build-linux-docker.sh`

---

## 方式三：桌面快捷方式 / 开机自启（可选）

程序内置「开机自启动」开关，打开后会在
`~/.config/autostart/BiliStreamRecorder.desktop` 生成自启动项。

想手动创建桌面菜单项，可复制 `packaging/BiliStreamRecorder.desktop` 到
`~/.local/share/applications/`，并修改其中的 `Exec=` 为你的实际路径：

```ini
[Desktop Entry]
Type=Application
Name=B站直播录播+自动投稿
Exec=/你的路径/dist/BiliStreamRecorder
Icon=/你的路径/assets/icon.ico
Terminal=false
Categories=Utility;
```

---

## 配置与日志位置

| 内容 | 位置 |
| --- | --- |
| 配置文件 | `~/.config/BiliStreamRecorder/config.json`（或 `$XDG_CONFIG_HOME`） |
| 日志 | 程序所在目录的 `log/`；不可写时回退到 `~/.config/BiliStreamRecorder/log/` |
| 录播 | 默认为程序目录的 `recordings/`，可在「设置」里改 |

---

## 常见问题

**Q：运行报 `No module named 'tkinter'`？**
未安装 tk 支持，见「方式一」第 1 步安装 `python3-tk` / `python3-tkinter`。

**Q：没有图形界面（纯命令行服务器）？**
本程序是桌面软件，需要图形环境（X11/Wayland）。无头服务器可考虑 Xvfb，但不推荐。

**Q：Wayland 下窗口/缩放异常？**
可尝试设置 `GDK_BACKEND=x11` 或 `QT_QPA_PLATFORM=xcb`（取决于桌面环境），或在 Xorg 会话下运行。

**Q：打包后的文件很大？**
PyInstaller 会把 Python 及依赖一起打包，属正常现象。
