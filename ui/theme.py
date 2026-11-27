"""界面主题：配色、字体、全局外观设置。

所有颜色集中在这里，界面模块只引用常量，方便以后换肤。
"""

import tkinter.font as tkfont

import customtkinter as ctk

# ---------------- 配色（深色 / 现代） ----------------
BG = "#0b0f14"          # 窗口底色
SIDEBAR = "#11161d"     # 侧边栏
CARD = "#151b23"        # 卡片
CARD_HOVER = "#1b222c"
BORDER = "#232c37"
TEXT = "#e6edf3"
TEXT_DIM = "#9aa7b4"
MUTED = "#6e7b8a"

ACCENT = "#00a1d6"      # B 站蓝
ACCENT_HOVER = "#28b8e8"
GREEN = "#2ecc71"
GREEN_HOVER = "#27ae60"
RED = "#ef4444"
RED_HOVER = "#d93c3c"
GRAY = "#39434f"
GRAY_HOVER = "#46525f"
PINK = "#fb7299"
PINK_HOVER = "#e2607f"

LOG_BG = "#070a0e"
LOG_FG = "#cfe8ef"

# ---------------- 尺寸 ----------------
CARD_RADIUS = 14
BTN_RADIUS = 10
PAD = 16

_CJK_CANDIDATES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
)

_MONO_CANDIDATES = (
    "Cascadia Mono",
    "Consolas",
    "JetBrains Mono",
    "DejaVu Sans Mono",
    "Courier New",
)

_family = None
_mono_family = None


def font_family() -> str:
    """挑一个系统里存在的 CJK 字体。"""
    global _family
    if _family:
        return _family
    try:
        families = set(tkfont.families())
    except Exception:
        families = set()
    for name in _CJK_CANDIDATES:
        if name in families:
            _family = name
            return name
    _family = "TkDefaultFont"
    return _family


def mono_family() -> str:
    global _mono_family
    if _mono_family:
        return _mono_family
    try:
        families = set(tkfont.families())
    except Exception:
        families = set()
    for name in _MONO_CANDIDATES:
        if name in families:
            _mono_family = name
            return name
    _mono_family = "Consolas"
    return _mono_family


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=font_family(), size=size, weight=weight)


def mono(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family=mono_family(), size=size)


def setup() -> None:
    """启动时调用一次：深色外观 + 关闭 DPI 自动缩放带来的模糊。"""
    try:
        ctk.set_appearance_mode("dark")
    except Exception:
        pass
