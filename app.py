"""B 站直播录播 + 自动投稿工具 —— 程序入口（深色现代界面 / customtkinter）。"""

from version import VERSION  # noqa: F401  兼容旧代码里的 from app import VERSION

from ui.main_window import APP_TITLE, App  # noqa: F401


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
