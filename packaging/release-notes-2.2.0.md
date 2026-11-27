# v2.2.0 —— 关闭时最小化到系统托盘

## ✨ 本次重点：托盘运行

点窗口右上角的 **×** 不再直接退出，程序缩到系统托盘继续跑——录制中、蹲播中都不会被误关。

- **右键托盘图标**：显示主界面 / 打开录播目录 / 退出程序
- **双击托盘图标**：直接回到主界面
- 首次缩到托盘会弹一条气泡提示，告诉你程序还在后台
- 后台期间录制、开播检测、定时任务全部照常工作
- 想改回「点 × 直接退出」：设置 → 自动化 → 其他 → 关掉「关闭时最小化到托盘」

> Windows 11 默认会把新出现的托盘图标收进「^ 显示隐藏的图标」，
> 点开就能看到；也可以把它拖到任务栏常驻。第一次的气泡提示就是干这个用的。

## 🔧 其它

- Linux 上托盘依赖 GTK / AppIndicator：**检测不到可用托盘时，程序会在 2 秒内自动把窗口弹回来**，
  不会出现「窗口没了又找不到图标」的情况；再点关闭即正常退出
- 托盘图标由程序自行绘制（内置 `assets/icon.ico`，缺失时用生成的蓝色图标兜底），不依赖外部文件
- 依赖新增 `pystray`

## ⬇️ 下载

| 文件 | 适用场景 |
| --- | --- |
| `BiliStreamRecorder-Setup-2.2.0-x86.exe` | **推荐**。安装版（Inno），32 位，32/64 位 Windows 通用 |
| `BiliStreamRecorder-Setup-2.2.0-x64.exe` | 安装版（Inno），64 位 Windows |
| `BiliStreamRecorder-Setup-2.2.0-x86.msi` | MSI，按用户安装、无需管理员 |
| `BiliStreamRecorder-Setup-2.2.0-x64.msi` | 同上，64 位 |
| `BiliStreamRecorder-x86.exe` | 免安装单文件，32/64 位通用 |
| `BiliStreamRecorder-x64.exe` | 免安装单文件，64 位 |

### 校验值（SHA256）

```
56D7B70133C5C0AAD960FFFFAF540BC0134F0367DA2772FCE2DBA249C0AD754E  BiliStreamRecorder-x64.exe
732319034DDB080853870A68D81584C490E99BD83A6E57DF8ABA8996B9B2DF79  BiliStreamRecorder-x86.exe
7BB685B0F5480A4E1717CDF0C0D411300236CE5010D1AA2117DFD234174E7FE1  BiliStreamRecorder-Setup-2.2.0-x64.exe
F9BBDBB364CA5C46F4D7F5AA79DC5C00FB6B61CA85E3BA72FC731266E1B82473  BiliStreamRecorder-Setup-2.2.0-x86.exe
20C1867C159634B719C3B8E3BF27826E81AAECE782071FC820D87760076BE6B3  BiliStreamRecorder-Setup-2.2.0-x64.msi
4A6932B9BFB7A7EB9EB99AC65D2DEA369815B0D9809DC1342BB8C1B2A4890E97  BiliStreamRecorder-Setup-2.2.0-x86.msi
F53AE7C33E1B458EAD6161E4E18BDE2F28038D76DCB13FD1B62ADFE0E4B8FCAA  BiliStreamRecorder
```

## ⬆️ 升级说明

- 旧配置自动沿用，录制 / 投稿 / 登录逻辑未变
- 升级后**默认开启**「关闭时最小化到托盘」；不习惯的话在设置里关掉即可
- 托盘状态下程序仍在运行，要彻底退出请用托盘菜单里的「退出程序」或任务管理器

---

完整更新日志见 [CHANGELOG.md](../CHANGELOG.md)。
