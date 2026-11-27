"""主窗口：录制状态、操作按钮、账号状态、实时日志。"""

import os
import queue
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog

import config
from controller import Controller
from logger import Logger
from uploader import check_login
from version import VERSION

from . import theme as T
from .login_dialog import QrLoginDialog
from .settings_window import SettingsWindow
from .widgets import action_button, card, card_title, ghost_button, pill

try:
    import autostart
except Exception:  # 非 Windows / 异常环境
    autostart = None

APP_TITLE = "B站直播录播 + 自动投稿"
AUTHOR_URL = "https://space.bilibili.com/1437520017"


class App(ctk.CTk):
    def __init__(self):
        T.setup()
        super().__init__(fg_color=T.BG)

        self.cfg = config.load_config()
        self.log = Logger(enabled=bool(self.cfg.get("log_enabled", True)))
        self.controller = Controller(self.log, self.cfg)

        self.settings_win = None
        self.login_win = None
        self._rec_start = None
        self._account_name = None
        # 后台线程不能直接碰 Tkinter 控件，统一投递到主线程执行
        self._ui_queue = queue.Queue()

        self.title(f"{APP_TITLE} v{VERSION}")
        w = min(1080, self.winfo_screenwidth() - 80)
        h = min(700, self.winfo_screenheight() - 100)
        self.geometry(f"{w}x{h}")
        self.minsize(900, 600)

        self._build_widgets()
        self._refresh_main()
        self.log(f"[日志] 日志目录: {self.log.log_dir}（记录开关：{'开' if self.log.enabled else '关'}）")

        # 启动时同步开机自启动（保持注册表/自启文件与配置一致）
        if autostart is not None:
            try:
                autostart.apply(bool(self.cfg.get("autostart")))
            except Exception:
                pass

        # 启动调度器（定时录制 / 开播自动检测）
        self.controller.scheduler.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._poll_log)
        self.after(300, self._poll_status)
        threading.Thread(target=self.controller.cleanup_old_recordings, daemon=True).start()
        threading.Thread(target=self._load_account_async, daemon=True).start()

    # ==================== 构建界面 ====================
    def _build_widgets(self) -> None:
        self.grid_columnconfigure(0, minsize=372)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        self._build_status_card(left)
        self._build_actions_card(left)
        self._build_account_card(left)
        self._build_log_card()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=64)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 8))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(
            title_box, text="◉ " + APP_TITLE, font=T.font(18, "bold"), text_color=T.TEXT
        ).pack(side="left")
        ctk.CTkLabel(
            title_box,
            text=f"v{VERSION}",
            font=T.font(11, "bold"),
            text_color=T.ACCENT,
            fg_color=T.CARD,
            corner_radius=8,
            height=22,
            width=52,
        ).pack(side="left", padx=(10, 0), pady=(2, 0))

        action_button(
            header, "❤ 支持作者", self._open_author,
            color=T.PINK, hover=T.PINK_HOVER, width=110, height=36, size=12,
        ).pack(side="right", padx=(8, 0))
        action_button(
            header, "⚙ 设置", self._open_settings, width=92, height=36, size=12
        ).pack(side="right")

    def _kv(self, parent, key: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=3)
        ctk.CTkLabel(
            row, text=key, width=64, anchor="w", font=T.font(12), text_color=T.MUTED
        ).pack(side="left")
        val = ctk.CTkLabel(row, text="—", anchor="w", font=T.font(13), text_color=T.TEXT)
        val.pack(side="left", fill="x", expand=True)
        return val

    def _build_status_card(self, parent) -> None:
        c = card(parent)
        c.pack(fill="x")
        card_title(c, "录制状态")
        self.room_lbl = self._kv(c, "直播间")
        self.name_lbl = self._kv(c, "主播")

        st_row = ctk.CTkFrame(c, fg_color="transparent")
        st_row.pack(fill="x", padx=18, pady=(6, 12))
        self.state_pill = pill(st_row, "就绪", T.GREEN)
        self.state_pill.pack(side="left")
        self.bytes_lbl = ctk.CTkLabel(
            st_row, text="", font=T.font(12), text_color=T.MUTED
        )
        self.bytes_lbl.pack(side="right")

    def _build_actions_card(self, parent) -> None:
        c = card(parent)
        c.pack(fill="x", pady=(10, 0))
        card_title(c, "操作")
        body = ctk.CTkFrame(c, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(10, 14))

        self.btn_start = action_button(
            body, "▶  开始录制", self._start, color=T.GREEN, hover=T.GREEN_HOVER, height=42, size=14
        )
        self.btn_start.pack(fill="x", pady=(0, 7))
        self.btn_stop = action_button(
            body, "■  停止录制", self._stop, color=T.RED, hover=T.RED_HOVER, height=42, size=14
        )
        self.btn_stop.pack(fill="x", pady=(0, 12))
        self.btn_upload = ghost_button(
            body, "↑  上传上次录播", self._upload_last, height=36, size=12
        )
        self.btn_upload.pack(fill="x", pady=(0, 7))
        self.btn_upload_file = ghost_button(
            body, "📁  上传本地文件", self._upload_file, height=36, size=12
        )
        self.btn_upload_file.pack(fill="x", pady=(0, 7))
        ghost_button(
            body, "📂  打开录播目录", self._open_output_dir, height=36, size=12
        ).pack(fill="x")

    def _build_account_card(self, parent) -> None:
        c = card(parent)
        c.pack(fill="x", pady=(10, 0))
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(
            head, text="投稿账号", font=T.font(13, "bold"), text_color=T.TEXT
        ).pack(side="left")

        self.account_lbl = ctk.CTkLabel(
            c, text="未登录", font=T.font(12), text_color=T.MUTED, anchor="w"
        )
        self.account_lbl.pack(fill="x", padx=18, pady=(2, 0))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(8, 14))
        action_button(
            row, "扫码登录", self._open_login, height=34, size=12
        ).pack(side="left")
        ghost_button(
            row, "测试登录", self._test_login, width=88, height=34, size=12
        ).pack(side="left", padx=(8, 0))

    def _build_log_card(self) -> None:
        c = card(self)
        c.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))

        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(
            head, text="实时日志", font=T.font(14, "bold"), text_color=T.TEXT
        ).pack(side="left")
        ghost_button(
            head, "清空显示", self._clear_log, width=80, height=28, size=11
        ).pack(side="right")

        self.log_text = ctk.CTkTextbox(
            c,
            fg_color=T.LOG_BG,
            text_color=T.LOG_FG,
            corner_radius=10,
            border_width=0,
            font=T.mono(12),
            wrap="word",
            activate_scrollbars=True,
        )
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(10, 14))
        self.log_text.configure(state="disabled")

    # ==================== 状态刷新 ====================
    def _post(self, fn) -> None:
        """把回调丢到主线程执行（供后台线程安全地更新界面）。"""
        self._ui_queue.put(fn)

    def _refresh_main(self) -> None:
        self.room_lbl.configure(text=str(self.cfg.get("room_id") or "—"))
        self.name_lbl.configure(text=str(self.cfg.get("streamer_name") or "—"))

    def _set_state(self, text: str, color: str) -> None:
        self.state_pill.configure(text=text, fg_color=color)

    # ==================== 动作 ====================
    def _open_author(self) -> None:
        try:
            webbrowser.open(AUTHOR_URL)
            self.log(f"[支持] 已打开作者主页: {AUTHOR_URL}")
        except Exception as e:
            self.log(f"[错误] 打开链接失败: {e}")

    def _open_settings(self) -> None:
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.lift()
            self.settings_win.focus_force()
            return
        self.settings_win = SettingsWindow(self)

    def _open_login(self) -> None:
        if self.login_win is not None and self.login_win.winfo_exists():
            self.login_win.lift()
            self.login_win.focus_force()
            return
        self.login_win = QrLoginDialog(
            self,
            on_success=self._on_login_success,
            log=self.log,
            on_close=lambda: setattr(self, "login_win", None),
        )

    def _on_login_success(self, cred: dict) -> None:
        for key in ("sessdata", "bili_jct", "buvid3", "dedeuserid", "ac_time_value"):
            if key in cred:
                self.cfg[key] = cred[key]
        config.save_config(self.cfg)
        self.log("[登录] 账号信息已保存，可以开始投稿了。")
        # 设置窗口若开着，同步刷新其中的 Cookie 输入框
        win = self.settings_win
        if win is not None and win.winfo_exists():
            try:
                win.sync_from_config()
            except Exception:
                pass
        threading.Thread(target=self._load_account_async, daemon=True).start()

    def _load_account_async(self) -> None:
        name = check_login(self.cfg)
        self._post(lambda: self._apply_account(name))

    def _apply_account(self, name) -> None:
        self._account_name = name
        if name:
            self.account_lbl.configure(text=f"已登录：{name}", text_color=T.GREEN)
        elif str(self.cfg.get("sessdata", "")).strip():
            self.account_lbl.configure(text="Cookie 已填写，但校验未通过", text_color=T.RED)
        else:
            self.account_lbl.configure(text="未登录（点击「扫码登录」获取权限）", text_color=T.MUTED)

    def _test_login(self) -> None:
        self.log("[登录] 正在校验 Cookie…")

        def worker():
            name = check_login(self.cfg)
            if name:
                self.log(f"[登录] 校验成功，当前账号: {name}")
            else:
                self.log("[登录] 校验失败，请点击「扫码登录」重新登录。")
            self._post(lambda: self._apply_account(name))

        threading.Thread(target=worker, daemon=True).start()

    def _start(self) -> None:
        if self.controller.start_recording(source="manual"):
            self.log("[手动] 开始录制。")
            self._rec_start = datetime.now()

    def _stop(self) -> None:
        self.log("[手动] 停止录制。")
        self.controller.stop_recording()
        self._rec_start = None

    def _upload_last(self) -> None:
        self.controller.upload_file(
            self.controller.last_recording, title=self.controller.current_title
        )

    def _upload_file(self) -> None:
        p = filedialog.askopenfilename(
            title="选择要上传的视频",
            filetypes=[("视频文件", "*.flv *.mp4 *.ts *.mkv"), ("所有文件", "*.*")],
        )
        if p:
            self.controller.upload_file(p)

    def _open_output_dir(self) -> None:
        path = str(self.cfg.get("output_dir", "")).strip() or self.controller.default_output_dir()
        try:
            os.makedirs(path, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log(f"[错误] 打开目录失败: {e}")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ==================== 轮询 ====================
    def _poll_log(self) -> None:
        try:
            self.log_text.configure(state="normal")
            lines = []
            while True:
                try:
                    lines.append(self.log.queue.get_nowait())
                except queue.Empty:
                    break
            if lines:
                self.log_text.insert("end", "\n".join(lines) + "\n")
                self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass
        self.after(120, self._poll_log)

    def _poll_status(self) -> None:
        # 执行后台线程投递过来的界面更新
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception:
                pass

        if self.controller.recording:
            mb = self.controller.recorder.bytes_written / 1024 / 1024
            self._set_state("● 录制中", T.RED)
            extra = f"已写入 {mb:.1f} MB"
            if self._rec_start:
                secs = int((datetime.now() - self._rec_start).total_seconds())
                extra += f"   时长 {secs // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}"
            self.bytes_lbl.configure(text=extra)
        elif self.controller.uploading:
            self._set_state("● 上传中", T.ACCENT)
            self.bytes_lbl.configure(text="")
        else:
            self._set_state("● 就绪", T.GREEN)
            self.bytes_lbl.configure(text="")
        self.btn_start.configure(state="disabled" if self.controller.recording else "normal")
        self.btn_stop.configure(state="normal" if self.controller.recording else "disabled")
        self.after(300, self._poll_status)

    # ==================== 关闭 ====================
    def _on_close(self) -> None:
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.collect_and_apply(silent=True)
        if self.login_win is not None and self.login_win.winfo_exists():
            try:
                self.login_win.close()
            except Exception:
                pass
        self.controller.shutdown()
        self.destroy()
