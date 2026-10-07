"""开机自启动（写入当前用户注册表 Run 项）"""

import os
import sys

try:
    import winreg
except ImportError:  # 非 Windows
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "BiliStreamRecorder"


def _command() -> str:
    """返回开机启动命令：打包后为 exe 路径，源码运行为 python + app.py。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    return f'"{sys.executable}" "{script}"'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except OSError:
        return False


def apply(enabled: bool) -> None:
    """开启/关闭开机自启动。"""
    if winreg is None:
        raise RuntimeError("当前系统不支持开机自启动设置")
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
    else:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
