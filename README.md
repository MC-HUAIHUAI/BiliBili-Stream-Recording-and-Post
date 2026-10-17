# BiliStreamRecorder

B 站直播**录播 + 自动投稿**一体化工具（横向 GUI，网页风格）。

- 指定任意 B 站直播间，以 **原画 1080p** 录制直播
- 录制完成后**自动投稿**到 B 站（指定账号），无需手动干预
- 投稿参数已按需求固定：**分区 = 生活-日常**、**标题 = 【xxxx年x月x日录播】xx的直播回放**、**创作声明内容无需标注**
- 支持**手动 / 定时 / 开播自动检测**三种录制触发方式
- 支持 **Windows 与 Linux**
- 纯本地运行，Cookie 仅保存在本机，不经过任何第三方服务器

> 📖 [使用教程](USAGE.md) ｜ 🪟 [Windows 安装](INSTALL-Windows.md) ｜ 🐧 [Linux 安装](INSTALL-Linux.md)

---

## 功能特性

| 功能 | 说明 |
| --- | --- |
| 横向界面 | 横向布局 + 网页风格，可选项用**开关**（滑块）呈现，独立设置窗口 |
| 录播 | 基于 [streamlink](https://github.com/streamlink/streamlink)，输出原画 1080p |
| 断线重连 | 直播流断开后每 5 秒重连一次、最多 3 次；断线前已录内容继续保留并追加，下播自动停止 |
| 自动投稿 | 基于 [bilibili-api-python](https://github.com/Nemo2011/bilibili-api)，录制完成自动上传 |
| 手动投稿 | 可随时上传「上次录播」或任意本地视频文件 |
| 定时录制 | 设定开始/结束时间，自动启停（支持跨天） |
| 开播检测 | 定时轮询直播间状态，检测到开播自动录制、下播自动停止 |
| 封面选择 | 封面可选「自动文字封面」或「自定义图片」（自动裁剪为 16:9） |
| 保存位置 | 录播缓存位置可自由选择（本地任意目录） |
| 保留天数 | 可设置录播保留天数，超期自动清理磁盘空间 |
| 空间保护 | 主位置剩余低于阈值（默认 20G）时自动切换备用目录；两者都不足时自动删除最早三天的录播 |
| 配置持久化 | 所有设置自动保存，下次启动无需重填 |
| 日志开关 | 可选是否写日志到磁盘；开启时在 `log\` 下按天保存并实时写 `latest.log` |
| 开机自启动 | 可选随系统启动（Windows 注册表 / Linux autostart） |
| 支持作者 | 界面内置「❤ 支持作者」按钮，指向作者 B 站主页 |
| 多平台 | Windows：x86（32 位，通用）/ x64；Linux：x86_64 单文件 |

---

## 环境要求

- **Windows** 10 / 11：已打包版本（exe/msi）**无需安装 Python**
- **Linux**：需要 Python 3 + tkinter（详见 [Linux 安装](INSTALL-Linux.md)）
- x86 版可在 32 位 / 64 位 Windows 上运行；x64 版仅限 64 位系统

---

## 快速开始

**Windows**：下载 `BiliStreamRecorder-x86.exe`（通用）双击运行 → [详细安装](INSTALL-Windows.md)

**Linux**：下载 `BiliStreamRecorder`（x86_64 单文件）→ `chmod +x BiliStreamRecorder && ./BiliStreamRecorder`
（需 glibc ≥ 2.35，详见 [Linux 安装](INSTALL-Linux.md)）

**从源码**：
```bash
git clone https://github.com/MC-HUAIHUAI/BiliBili-Stream-Recording-and-Post.git
cd BiliBili-Stream-Recording-and-Post
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```

使用步骤见 **[使用教程](USAGE.md)**。

---

## 从源码运行

```powershell
git clone <repo-url>
cd <repo>
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python app.py
```

> 国内网络建议为 pip 配置镜像：
> `.\venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

---

## 获取投稿账号 Cookie

录制不需要登录；**投稿需要**投稿账号的 Cookie。获取步骤：

1. 用浏览器登录 bilibili.com（使用你的投稿账号）
2. 按 `F12` 打开开发者工具 → 切到「应用/Application」→「Cookie」→ `https://www.bilibili.com`
3. 复制以下字段填入软件对应输入框：
   - `SESSDATA`（必填）
   - `bili_jct`（必填，即 csrf token）
   - `buvid3`（推荐，用于更稳定登录态）
   - `DedeUserID`（推荐）
4. 点击「测试登录」校验是否有效

> **安全提醒**：Cookie 相当于账号登录凭证，请勿泄露。本工具仅将 Cookie 保存在本机
> `%APPDATA%\BiliStreamRecorder\config.json`，绝不外传。

---

## 投稿参数说明

| 参数 | 值 |
| --- | --- |
| 分区 | 生活 - 日常（tid = 21） |
| 标题 | `【xxxx年x月x日录播】{主播名}的直播回放`（可自定义模板，见下） |
| 标签 | 默认 `录播,直播`（可自定义） |
| 创作声明 | 不标注（`neutral_mark` 未设置） |
| 原创声明 | 原创（`copyright = 1`） |

### 标题模板

默认模板：`【{date}录播】{name}的直播回放`

- `{date}` 会被替换为**直播日期**（即开始录制那天的日期，跨午夜直播按开播日期计算），如 `2026年9月24日`
- `{name}` 会被替换为主播名
- **其余文字（如「蕾蕾的直播回放」中的「的直播回放」部分）均可自由修改**

例如想改成 `【{date}录播】蕾蕾的直播回放`（后缀写死），或 `{date} 蕾蕾 直播录像` 都可以，
直接在 GUI 的「标题模板」输入框里编辑即可。

---

## 打包（生成 exe / msi 安装包）

> 支持双架构：`-Arch x86` 生成 32 位（x86/x64 通用），`-Arch x64` 生成 64 位。
> 需要两套虚拟环境：`venv`（64 位 Python）与 `venv32`（32 位 Python），依赖见 `requirements.txt`。

### 1. 单文件 exe

```powershell
.\packaging\build.ps1 -Arch x64    # 产物: dist\BiliStreamRecorder-x64.exe
.\packaging\build.ps1 -Arch x86    # 产物: dist\BiliStreamRecorder-x86.exe（通用）
```

### 2. exe 安装包（Inno Setup）

1. 安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. 先运行 `.\packaging\build.ps1 -Arch <x86|x64>` 生成对应 exe
3. 命令行编译：
   ```powershell
   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp /DArch=x64 packaging\bili_recorder.iss
   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp /DArch=x86 packaging\bili_recorder.iss
   ```
4. 产物: `dist\BiliStreamRecorder-Setup-2.0.1-x64.exe` / `-x86.exe`

### 3. MSI 安装包（WiX Toolset v3）

1. 下载 [WiX Toolset v3](https://wixtoolset.org/releases/)（解压出 `candle.exe` / `light.exe`）
2. 先运行 `.\packaging\build.ps1 -Arch <x86|x64>` 生成对应 exe
3. 执行（以 x64 为例，x86 同理把 `-dArch` 和输出名改为 x86）：
   ```powershell
   candle.exe -dArch=x64 packaging\bili_recorder.wxs -o dist\obj\
   light.exe dist\obj\bili_recorder.wixobj -o dist\BiliStreamRecorder-Setup-2.0.1-x64.msi
   ```
4. 产物: `dist\BiliStreamRecorder-Setup-2.0.1-x64.msi` / `-x86.msi`

> 一键构建全部（两个 exe + 4 个安装包）：`.\packaging\build-all.ps1`

---

## 项目结构

```
├── app.py              # GUI 入口（横向布局 / 网页风格 / 设置窗口）
├── recorder.py         # 直播录制（streamlink，1080p，断线重连）
├── uploader.py         # B 站投稿上传（bilibili-api-python）
├── scheduler.py        # 定时 / 开播自动检测调度
├── live.py             # 直播间信息查询
├── config.py           # 配置读写（跨平台路径）
├── autostart.py        # 开机自启动（Windows 注册表 / Linux .desktop）
├── utils.py            # 标题 / 文件名 / 磁盘空间等工具
├── requirements.txt
├── USAGE.md            # 使用教程
├── INSTALL-Windows.md  # Windows 安装指南
├── INSTALL-Linux.md    # Linux 安装指南
├── packaging/
│   ├── build.ps1              # Windows PyInstaller 打包（-Arch x86|x64）
│   ├── build-all.ps1          # Windows 一键构建全部产物
│   ├── build-linux.sh         # Linux PyInstaller 打包
│   ├── run-linux.sh           # Linux 源码运行
│   ├── BiliStreamRecorder.desktop
│   ├── bili_recorder.iss      # Inno Setup 脚本（exe 安装包）
│   └── bili_recorder.wxs      # WiX 脚本（msi 安装包）
└── assets/icon.ico
```

---

## 常见问题

**Q：录制出来的不是 1080p？**
原画 1080p 部分直播间需要登录才能拉流，请在 GUI 中填写投稿账号的 `SESSDATA`（录制时会携带该 Cookie）。

**Q：录制的文件是什么格式？**
FLV（直播原画流），B 站投稿支持该格式。

**Q：Cookie 会不会失效？**
会，Cookie 有有效期，失效后「测试登录」会失败，重新登录 bilibili.com 复制新的即可。

**Q：为什么提示「缺少 Cookie」？**
投稿至少需要 `SESSDATA` 与 `bili_jct` 两个字段。

---

## 免责声明

本项目仅供学习与技术交流，请遵守 B 站用户协议及相关法律法规，录制与上传前请确认已获得主播/版权方授权，禁止用于任何侵权用途。使用本工具产生的一切后果由使用者自行承担。

## License

[MIT](LICENSE)
