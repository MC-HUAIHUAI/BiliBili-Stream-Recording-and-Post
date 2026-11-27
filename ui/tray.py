"""系统托盘图标：关闭主窗口后程序继续在后台运行。

- Windows / Linux 通用（Linux 需要 GTK 或 AppIndicator，缺依赖时自动降级为"关闭即退出"）
- 托盘回调统一通过 app._post() 投递回 Tk 主线程，避免跨线程操作控件
"""

import os
import sys
import threading

from PIL import Image, ImageDraw

try:
    import pystray
except Exception:  # 没有托盘库（或缺少系统依赖）时降级
    pystray = None


def _icon_path() -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets", "icon.ico")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "assets", "icon.ico")


def _fallback_image(size: int = 64) -> Image.Image:
    """没有 icon 文件时画一个，保证托盘一定能显示。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=14, fill=(0, 161, 214, 255))
    d.polygon([(24, 18), (24, 46), (48, 32)], fill=(255, 255, 255, 255))
    return img


def load_icon_image() -> Image.Image:
    try:
        path = _icon_path()
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
    except Exception:
        pass
    return _fallback_image()


class TrayIcon:
    """托盘图标的生命周期封装。"""

    def __init__(self, app):
        self.app = app
        self._icon = None
        self._thread = None
        self._failed = False

    @property
    def available(self) -> bool:
        return pystray is not None and not self._failed

    @property
    def running(self) -> bool:
        return self._icon is not None

    @property
    def visible(self) -> bool:
        """托盘图标是否真的显示出来了（没有托盘宿主的桌面会一直是 False）。"""
        try:
            return bool(self._icon is not None and getattr(self._icon, "visible", False))
        except Exception:
            return False

    def start(self) -> bool:
        if self.running:
            return True
        if not self.available:
            return False
        try:
            menu = pystray.Menu(
                pystray.MenuItem("显示主界面", self._on_show, default=True),
                pystray.MenuItem("打开录播目录", self._on_open_dir),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出程序", self._on_quit),
            )
            self._icon = pystray.Icon(
                "BiliStreamRecorder",
                load_icon_image(),
                "B站直播录播 + 自动投稿",
                menu,
            )
            self._thread = threading.Thread(
                target=self._run, name="tray-icon", daemon=True
            )
            self._thread.start()
            return True
        except Exception as e:
            self._failed = True
            self._icon = None
            try:
                self.app.log(f"[托盘] 创建托盘图标失败，关闭窗口将直接退出: {e}")
            except Exception:
                pass
            return False

    def _run(self) -> None:
        try:
            self._icon.run()
        except Exception as e:
            self._failed = True
            try:
                self.app.log(f"[托盘] 托盘线程异常退出: {e}")
            except Exception:
                pass

    # ---------- 菜单回调（在托盘线程里，必须转投主线程） ----------
    def _on_show(self, icon=None, item=None) -> None:
        self.app._post(self.app.show_from_tray)

    def _on_open_dir(self, icon=None, item=None) -> None:
        self.app._post(self.app._open_output_dir)

    def _on_quit(self, icon=None, item=None) -> None:
        self.app._post(self.app.quit_app)

    def notify(self, message: str, title: str = "B站直播录播 + 自动投稿") -> None:
        try:
            if self._icon:
                self._icon.notify(message, title)
        except Exception:
            pass

    def stop(self) -> None:
        try:
            if self._icon:
                self._icon.stop()
        except Exception:
            pass
        self._icon = None
