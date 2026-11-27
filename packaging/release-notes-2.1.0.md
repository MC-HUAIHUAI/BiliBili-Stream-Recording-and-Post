# v2.1.0 —— 扫码登录 + 深色新界面

## ✨ 本次重点：扫码登录

投稿账号不用再手动抓 Cookie 了。

- 主界面「投稿账号」卡片点 **扫码登录**（设置 → 投稿账号 里也有同一个按钮）
- 用 **B站 手机客户端** → 我的 → 扫一扫
- 手机上点「确认登录」，程序自动保存 `SESSDATA` / `bili_jct` / `buvid3` / `DedeUserID`
- 二维码 3 分钟内有效，过期点「刷新二维码」；登录成功后主界面直接显示账号昵称

原来的手动填 Cookie 入口仍然保留在「设置 → 投稿账号 → 手动 Cookie」，作为高级选项。

## 🎨 界面重构

- 换用 **customtkinter**：深色现代风格、卡片式布局、圆角控件、真实开关
- 设置窗口改为 **左侧分类导航 + 右侧分页**：直播与标题 / 存储与空间 / 封面 / 投稿账号 / 自动化 / 关于
- 主窗口左右分栏：左侧「录制状态 + 操作 + 投稿账号」，右侧「实时日志」
- 录制中实时显示已录时长；新增「打开录播目录」按钮

## 🔧 修复

- 修复 Windows PowerShell 5.1 下 `packaging/*.ps1` 与 `*.iss` / `*.wxs` 因缺少 UTF-8 BOM、
  中文注释被按 GBK 解码，导致**打包脚本直接解析失败**的问题
- 后台线程更新界面改为经主线程队列投递，避免跨线程操作 Tkinter

## ⬇️ 下载

| 文件 | 适用场景 |
| --- | --- |
| `BiliStreamRecorder-Setup-2.1.0-x86.exe` | **推荐**。安装版（Inno），32 位，32/64 位 Windows 通用 |
| `BiliStreamRecorder-Setup-2.1.0-x64.exe` | 安装版（Inno），64 位 Windows |
| `BiliStreamRecorder-Setup-2.1.0-x86.msi` | MSI 安装包，按计算机安装，适合域环境 / `msiexec /qn` 静默部署 |
| `BiliStreamRecorder-Setup-2.1.0-x64.msi` | 同上，64 位 |
| `BiliStreamRecorder-x86.exe` | 免安装单文件，32/64 位通用，绿色版 |
| `BiliStreamRecorder-x64.exe` | 免安装单文件，64 位 |
| `BiliStreamRecorder` | Linux x86_64 单文件（glibc ≥ 2.35） |

### 校验值（SHA256）

```
51BE4F5ADB0AEFD2259E73DAA77D4257B268B76C9ECBA7360AE74C3F1AD42661  BiliStreamRecorder-Setup-2.1.0-x64.exe
86C5F46B1FE29B6B478F68B4E672C7BA0647D674672874FBBBA979C9DEE24FED  BiliStreamRecorder-Setup-2.1.0-x86.exe
D8E9B82F962EA5CD6F94EAC0F1C73B027A603861713ABBC4418168115929C4BC  BiliStreamRecorder-Setup-2.1.0-x64.msi
104D88477BF34C43CC42EC4B3BEF1D49B123FC161EC98B2ADE30D2527FEAA41F  BiliStreamRecorder-Setup-2.1.0-x86.msi
672629F6E56C77EE6A53ED3053AAE7098E71EA1904F802A032E184459569E3F9  BiliStreamRecorder-x64.exe
4B248001C5327D9DFF28EC05A407F7E38ECD78B19863F5A7B123A9F3A7521FEB  BiliStreamRecorder-x86.exe
3396F1AB886F17965C75E44EE560FB460B140FED380E1CCC44142F49B3FF3C1A  BiliStreamRecorder
```

## ⬆️ 升级说明

- 旧配置（`%APPDATA%\BiliStreamRecorder\config.json`）自动沿用，原有 Cookie 仍然有效，可直接继续投稿
- 想改用扫码登录，点一次「扫码登录」即可覆盖旧 Cookie
- 本版本只改了界面与登录流程，录制 / 投稿 / 调度逻辑未变，录播文件与日志位置不变

## 🐧 关于 Linux 版

`BiliStreamRecorder`（43.1 MB）在 **Ubuntu 22.04 容器**内用 PyInstaller 构建，已随附本版本。

```bash
chmod +x BiliStreamRecorder
./BiliStreamRecorder
```

- 需要 **glibc ≥ 2.35**（Ubuntu 22.04+ / Debian 12+ / Fedora 36+）
- 需要桌面图形环境（X11/Wayland）；无头服务器可用 `xvfb-run` 但不推荐
- 若系统较旧，请按 [Linux 安装指南](../INSTALL-Linux.md) 从源码运行

重新构建：

```bash
./venv/bin/pip install -r requirements.txt pyinstaller
./packaging/build-linux.sh
# 或在装有 Docker 的机器上
docker run --rm -v "$PWD:/src" ubuntu:22.04 bash /src/packaging/build-linux-docker.sh
```

---

完整更新日志见 [CHANGELOG.md](../CHANGELOG.md)。
