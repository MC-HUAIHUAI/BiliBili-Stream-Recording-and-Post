"""日志模块：线程安全日志，输出到 GUI 队列并可实时写入磁盘。"""

import os
import queue
import threading
from datetime import datetime

import config


class Logger:
    """线程安全日志：输出到 GUI 队列，并可实时写入 log 目录。

    - log\\<YYYY-MM-DD>.log : 每日日志（按天追加，自动跨天）
    - log\\latest.log        : 最新实时日志（每次启动覆盖）
    """

    def __init__(self, enabled: bool = True):
        self.queue = queue.Queue()
        self._lock = threading.Lock()
        self.enabled = bool(enabled)
        self.log_dir = config.get_log_dir()
        now = datetime.now()
        self._daily_date = now.strftime("%Y-%m-%d")
        self.daily_path = os.path.join(self.log_dir, self._daily_date + ".log")
        self.latest_path = os.path.join(self.log_dir, "latest.log")
        try:
            with open(self.latest_path, "w", encoding="utf-8") as f:
                f.write("")
        except OSError:
            pass
        self._session_header()

    def _session_header(self) -> None:
        header = f"===== 会话开始 {datetime.now():%Y-%m-%d %H:%M:%S} ====="
        self._append_lines([header])

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if self.enabled:
            self._append_lines(["----- 已启用日志记录 -----"])

    def __call__(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.queue.put(line)
        self._append_lines([line])

    def _append_lines(self, lines) -> None:
        if not self.enabled:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            if today != self._daily_date:
                self._daily_date = today
                self.daily_path = os.path.join(self.log_dir, today + ".log")
            for path in (self.daily_path, self.latest_path):
                try:
                    with open(path, "a", encoding="utf-8") as f:
                        for ln in lines:
                            f.write(ln + "\n")
                except OSError:
                    pass
