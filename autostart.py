"""开机自启动（Windows 注册表 Run 项 / Linux autostart .desktop）"""

import os
import sys

import config

try:
    import winreg
except ImportError:  # 非 Windows
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "BiliStreamRecorder"


def _command() -> str:
    """返回开机启动命令：打包后为可执行文件，源码运行为 python + app.py。"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    return f'"{sys.executable}" "{script}"'


def _desktop_file() -> str:
    return os.path.join(config.get_autostart_dir(), f"{APP_NAME}.desktop")


def is_enabled() -> bool:
    if os.name == "nt":
        if winreg is None:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(value)
        except OSError:
            return False
    return os.path.exists(_desktop_file())


def apply(enabled: bool) -> None:
    """开启/关闭开机自启动。"""
    if os.name == "nt":
        _apply_windows(enabled)
    else:
        _apply_linux(enabled)


def _apply_windows(enabled: bool) -> None:
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


def _apply_linux(enabled: bool) -> None:
    path = _desktop_file()
    if enabled:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={_command()}\n"
            "X-GNOME-Autostart-enabled=true\n"
            "Terminal=false\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
