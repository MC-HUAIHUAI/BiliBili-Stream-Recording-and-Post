# Windows 安装指南

`B站直播录播 + 自动投稿` 在 Windows 上共有 **3 种使用方式**，任选其一即可。
所有方式都**无需安装 Python**。

> 想了解怎么用？请看 [使用教程](USAGE.md)。

---

## 方式一：免安装单文件（推荐）

适合：想立刻用、不想安装的用户。

1. 到 [Releases](https://github.com/MC-HUAIHUAI/BiliBili-Stream-Recording-and-Post/releases) 下载：
   - 32 位系统 / 不确定：`BiliStreamRecorder-x86.exe`（x86/x64 通用）
   - 64 位系统：`BiliStreamRecorder-x64.exe`
2. 放到任意目录（例如 `D:\Tools\`），**双击即可运行**。
3. 程序会在所在目录生成 `log\`（日志）与 `recordings\`（录播，若使用默认位置）文件夹。

> 优点：绿色、免安装、可放 U 盘。
> 注意：程序**不要放在需要管理员权限才能写入**的目录（如 `C:\Program Files` 根目录），否则日志会回退到 `%APPDATA%\BiliStreamRecorder\log`。

---

## 方式二：exe 安装包（Inno Setup）

适合：想要开始菜单 / 桌面快捷方式、能从「控制面板」卸载的用户。

1. 下载 `BiliStreamRecorder-Setup-2.0.0-x86.exe`（通用）或 `-x64.exe`
2. 双击运行，按提示下一步即可（**按当前用户安装，不需要管理员权限**）
3. 默认安装到：`%LOCALAPPDATA%\Programs\BiliStreamRecorder\`
4. 安装完成后会自动创建开始菜单与桌面快捷方式

**卸载**：设置 → 应用 → 找到 `B站直播录播+自动投稿` → 卸载；
或运行安装目录下的 `unins000.exe`。

---

## 方式三：MSI 安装包（WiX）

适合：企业 / 域环境、需要用 `msiexec` 静默部署的场景。

1. 下载 `BiliStreamRecorder-Setup-2.0.0-x86.msi`（通用）或 `-x64.msi`
2. 双击安装（**按计算机安装到 `C:\Program Files`，需要管理员权限**）
3. 静默安装命令：
   ```powershell
   msiexec /i BiliStreamRecorder-Setup-2.0.0-x64.msi /qn
   ```
4. 静默卸载：
   ```powershell
   msiexec /x BiliStreamRecorder-Setup-2.0.0-x64.msi /qn
   ```

> 注意：MSI 安装到 `Program Files` 后，普通用户**无写入权限**，日志会自动回退到
> `%APPDATA%\BiliStreamRecorder\log\`。若希望日志写进安装目录，请改用**方式一或方式二**。

---

## 三种方式对比

| 方式 | 需要管理员 | 安装目录 | 日志位置 | 卸载方式 |
| --- | --- | --- | --- | --- |
| 单文件 exe | 否 | 自己放的位置 | 同目录 `log\` | 直接删文件 |
| exe 安装包 | 否（按用户） | `%LOCALAPPDATA%\Programs\...` | 同目录 `log\` | 应用里卸载 |
| msi | 是（按计算机） | `C:\Program Files\...` | 回退到 `%APPDATA%` | `msiexec /x` |

---

## x86 还是 x64？

- **只想要一个能用的** → 选 **x86**（32 位），它在 32 位和 64 位 Windows 上都能运行。
- 64 位系统想榨性能 → 选 x64。

---

## 常见问题

**Q：Windows 提示“已保护你的电脑”（SmartScreen）？**
未签名的个人软件常见提示。点「更多信息」→「仍要运行」即可。

**Q：杀毒软件报毒？**
PyInstaller 打包的程序偶被误报，添加信任即可。源码完全公开，可自行 [从源码运行](USAGE.md#从源码运行)。

**Q：双击没反应？**
请确认不是放在了无写入权限的目录。可先改用单文件 exe 放到 `D:\` 下试试。
