"""B 站直播录播 + 自动投稿工具 —— GUI 入口（横向布局 / 网页风格）"""

import os
import queue
import threading
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import tkinter as tk
import tkinter.font as tkfont

import config
import utils
from recorder import Recorder
from scheduler import Scheduler
from uploader import BiliUploader, check_login

try:
    import autostart
except Exception:  # 非 Windows / 异常环境
    autostart = None

APP_TITLE = "B站直播录播 + 自动投稿"
VERSION = "2.0.2"
AUTHOR_URL = "https://space.bilibili.com/1437520017"

# ---- 配色（网页风格）----
COL_BG = "#eef2f7"
COL_CARD = "#ffffff"
COL_ACCENT = "#00a1d6"
COL_ACCENT2 = "#0091c2"
COL_GREEN = "#27ae60"
COL_GREEN2 = "#1e8f4e"
COL_RED = "#e74c3c"
COL_RED2 = "#c0392b"
COL_GRAY = "#5b6b7d"
COL_GRAY2 = "#47576a"
COL_TEXT = "#22303f"
COL_MUTED = "#8a94a6"
COL_BORDER = "#dbe3ec"
COL_LOG_BG = "#0f1a24"
COL_LOG_FG = "#cfe8ef"

UI_FONT = "TkDefaultFont"


def pick_font() -> str:
    try:
        families = set(tkfont.families())
    except Exception:
        return "TkDefaultFont"
    for name in (
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ):
        if name in families:
            return name
    return "TkDefaultFont"


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


class ToggleSwitch(tk.Canvas):
    """网页风格的开关控件（代替复选框）。"""

    ON = "#00a1d6"
    OFF = "#c3ccd7"

    def __init__(self, master, variable=None, command=None, bg=None, width=46, height=24):
        parent_bg = bg or master.cget("bg")
        super().__init__(
            master, width=width, height=height, highlightthickness=0, bd=0, bg=parent_bg
        )
        self.var = variable or tk.BooleanVar()
        self.command = command
        self.w = width
        self.h = height
        self._draw()
        self.bind("<Button-1>", self._toggle)
        self.var.trace_add("write", lambda *a: self._draw())

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kwargs)

    def _draw(self):
        self.delete("all")
        on = bool(self.var.get())
        color = self.ON if on else self.OFF
        r = self.h / 2
        self._round_rect(1, 1, self.w - 1, self.h - 1, r, fill=color, outline=color)
        d = self.h - 6
        x = (self.w - d - 3) if on else 3
        self.create_oval(x, 3, x + d, self.h - 3, fill="#ffffff", outline="#ffffff")

    def _toggle(self, event=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()


class Controller:
    """录制 / 上传 / 调度的控制中心。"""

    def __init__(self, log, cfg: dict):
        self.log = log
        self.cfg = cfg
        self.recorder = Recorder(log)
        self.uploader = BiliUploader(log)
        self.scheduler = Scheduler(self, log)
        self.recording = False
        self.recording_source = None
        self.last_recording = None
        self.current_title = None

    @property
    def uploading(self) -> bool:
        return self.uploader.uploading

    def default_output_dir(self) -> str:
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "recordings")

    def _pick_output_dir(self) -> str:
        primary = str(self.cfg.get("output_dir", "")).strip() or self.default_output_dir()
        backup = str(self.cfg.get("backup_dir", "")).strip()
        try:
            min_gb = float(self.cfg.get("min_free_gb", 20) or 0)
        except (TypeError, ValueError):
            min_gb = 20.0

        for d in (primary, backup):
            if d:
                try:
                    os.makedirs(d, exist_ok=True)
                except Exception:
                    pass

        if min_gb <= 0:
            return primary

        free_p = utils.free_space_gb(primary)
        if free_p >= min_gb:
            self.log(f"[空间] 保存位置剩余 {free_p:.1f}G，充足（阈值 {min_gb:.0f}G）。")
            return primary
        self.log(f"[空间] 保存位置剩余 {free_p:.1f}G，低于阈值 {min_gb:.0f}G。")

        if backup:
            free_b = utils.free_space_gb(backup)
            if free_b >= min_gb:
                self.log(f"[空间] 切换到备用保存位置（剩余 {free_b:.1f}G）：{backup}")
                return backup
            self.log(f"[空间] 备用保存位置剩余 {free_b:.1f}G，也不足。")
        else:
            self.log("[空间] 未设置备用保存位置。")

        self.log("[空间] 两个位置均不足，自动删除最早三天的录播…")
        removed = utils.delete_earliest_days(primary, 3, self.log)
        if backup:
            removed += utils.delete_earliest_days(backup, 3, self.log)
        self.log(f"[空间] 已清理 {removed} 个较早录播文件。")

        free_p = utils.free_space_gb(primary)
        if free_p >= min_gb:
            return primary
        if backup:
            free_b = utils.free_space_gb(backup)
            if free_b >= min_gb:
                self.log(f"[空间] 清理后切换到备用保存位置：{backup}")
                return backup
            if free_b > free_p:
                self.log(f"[警告] 空间仍不足，改用剩余较大的备用目录：{backup}")
                return backup
        self.log(f"[警告] 空间仍不足（剩余 {free_p:.1f}G），继续使用主保存位置。")
        return primary

    def start_recording(self, source: str = "manual") -> bool:
        if self.recording:
            return False
        room = str(self.cfg.get("room_id", "")).strip()
        if not room:
            self.log("[错误] 请先在设置中填写直播间号。")
            return False
        out_dir = self._pick_output_dir()
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.log(f"[错误] 无法创建输出目录: {e}")
            return False

        name = str(self.cfg.get("streamer_name", "")).strip() or "主播"
        start_dt = datetime.now()
        title = utils.build_title(self.cfg.get("title_template", ""), name, start_dt)
        filename = utils.make_output_filename(name, ".flv")
        path = os.path.join(out_dir, filename)

        self.log(f"[标题] {title}  （直播日期: {utils.chinese_date(start_dt)}）")
        self.last_recording = path
        self.current_title = title
        self.recording_source = source
        self.recording = True
        self.recorder.start(
            room,
            path,
            self.cfg.get("sessdata", ""),
            self.cfg.get("buvid3", ""),
            on_finish=self._on_recording_finished,
        )
        return True

    def stop_recording(self) -> None:
        if not self.recording:
            return
        self.recorder.stop()

    def _on_recording_finished(self) -> None:
        self.recording = False
        self.recording_source = None
        path = self.last_recording
        if (
            bool(self.cfg.get("auto_upload"))
            and path
            and os.path.exists(path)
            and os.path.getsize(path) > 0
        ):
            self.log("[自动] 录制完成，开始自动上传。")
            self.upload_file(path, title=self.current_title)
        self.cleanup_old_recordings()

    def cleanup_old_recordings(self) -> None:
        days = int(self.cfg.get("retention_days", 0) or 0)
        if days <= 0:
            return
        out_dir = str(self.cfg.get("output_dir", "")).strip() or self.default_output_dir()
        removed = utils.cleanup_old_files(out_dir, days, self.log)
        if removed:
            self.log(f"[清理] 本次共清理 {removed} 个过期录播文件。")

    def upload_file(self, path: str, title: str = None) -> None:
        if self.uploader.uploading:
            self.log("[提示] 已有上传任务进行中。")
            return
        if not path or not os.path.exists(path):
            self.log("[错误] 文件不存在，无法上传。")
            return
        if not title:
            title = self._title_for_file(path)
        self.log(f"[上传] 准备上传: {path}")
        self.uploader.upload(path, title, self.cfg)

    def _title_for_file(self, path: str) -> str:
        name = str(self.cfg.get("streamer_name", "")).strip() or "主播"
        dt = utils.datetime_from_file(path)
        return utils.build_title(self.cfg.get("title_template", ""), name, dt)

    def shutdown(self) -> None:
        self.scheduler.stop()
        if self.recording:
            self.recorder.stop(timeout=5)


# =========================== 主窗口 ===========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        global UI_FONT

        self.cfg = config.load_config()
        self.log = Logger(enabled=bool(self.cfg.get("log_enabled", True)))
        self.controller = Controller(self.log, self.cfg)

        self.settings_win = None
        self._loading = False

        self.title(f"{APP_TITLE} v{VERSION}")
        w = min(1000, self.winfo_screenwidth() - 80)
        h = min(620, self.winfo_screenheight() - 100)
        self.geometry(f"{w}x{h}")
        self.minsize(820, 520)
        self.configure(bg=COL_BG)

        UI_FONT = pick_font()
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
        self.after(100, self._poll_log)
        self.after(300, self._poll_status)
        threading.Thread(target=self.controller.cleanup_old_recordings, daemon=True).start()

    # ---------- 构建 ----------
    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=COL_CARD, highlightbackground=COL_BORDER,
                         highlightthickness=1)
        if title:
            tk.Label(outer, text=title, bg=COL_CARD, fg=COL_TEXT,
                     font=(UI_FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        body = tk.Frame(outer, bg=COL_CARD)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        return outer, body

    def _button(self, parent, text, command, bg, bg2, width=13):
        return tk.Button(
            parent, text=text, command=command, bg=bg, fg="#ffffff",
            activebackground=bg2, activeforeground="#ffffff", relief="flat",
            bd=0, padx=10, pady=8, cursor="hand2", width=width,
            font=(UI_FONT, 10, "bold"), disabledforeground="#e8edf2",
        )

    def _build_widgets(self):
        # 顶栏
        header = tk.Frame(self, bg=COL_CARD, highlightbackground=COL_BORDER,
                          highlightthickness=1)
        header.pack(side="top", fill="x")
        tk.Label(header, text="◉ " + APP_TITLE, bg=COL_CARD, fg=COL_TEXT,
                 font=(UI_FONT, 14, "bold")).pack(side="left", padx=16, pady=10)
        tk.Label(header, text=f"v{VERSION}", bg=COL_CARD, fg=COL_MUTED,
                 font=(UI_FONT, 9)).pack(side="left", pady=(16, 10))

        self._button(header, "❤ 支持作者", self._open_author, "#fb7299", "#e35f85", 10).pack(
            side="right", padx=(6, 16), pady=8
        )
        self._button(header, "⚙ 设置", self._open_settings, COL_ACCENT, COL_ACCENT2, 8).pack(
            side="right", padx=6, pady=8
        )

        body = tk.Frame(self, bg=COL_BG)
        body.pack(side="top", fill="both", expand=True, padx=12, pady=12)

        # 左：控制
        left = tk.Frame(body, bg=COL_BG, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        info_card, info = self._card(left, "录制状态")
        info_card.pack(fill="x")
        self.room_lbl = tk.Label(info, text="直播间: —", bg=COL_CARD, fg=COL_TEXT,
                                 font=(UI_FONT, 10), anchor="w")
        self.room_lbl.pack(fill="x", pady=2)
        self.name_lbl = tk.Label(info, text="主播: —", bg=COL_CARD, fg=COL_TEXT,
                                 font=(UI_FONT, 10), anchor="w")
        self.name_lbl.pack(fill="x", pady=2)
        self.state_lbl = tk.Label(info, text="状态: 就绪", bg=COL_CARD, fg=COL_GREEN,
                                  font=(UI_FONT, 10, "bold"), anchor="w")
        self.state_lbl.pack(fill="x", pady=(6, 2))
        self.bytes_lbl = tk.Label(info, text="", bg=COL_CARD, fg=COL_MUTED,
                                  font=(UI_FONT, 9), anchor="w")
        self.bytes_lbl.pack(fill="x")

        btn_card, btnbody = self._card(left, "操作")
        btn_card.pack(fill="x", pady=(12, 0))
        self.btn_start = self._button(btnbody, "▶ 开始录制", self._start, COL_GREEN, COL_GREEN2, 16)
        self.btn_start.pack(fill="x", pady=4)
        self.btn_stop = self._button(btnbody, "■ 停止录制", self._stop, COL_RED, COL_RED2, 16)
        self.btn_stop.pack(fill="x", pady=4)
        self.btn_upload = self._button(btnbody, "⬆ 上传上次录播", self._upload_last, COL_GRAY, COL_GRAY2, 16)
        self.btn_upload.pack(fill="x", pady=4)
        self.btn_upload_file = self._button(btnbody, "📁 上传本地文件", self._upload_file, COL_GRAY, COL_GRAY2, 16)
        self.btn_upload_file.pack(fill="x", pady=4)

        tip = tk.Label(
            left, bg=COL_BG, fg=COL_MUTED, justify="left", anchor="w",
            font=(UI_FONT, 8),
            text="提示：录播与投稿参数请在右上角「设置」中配置。\n录制为原画 1080p；断线自动重连（最多 3 次）。",
        )
        tip.pack(fill="x", pady=(12, 0))

        # 右：日志
        log_card, logbody = self._card(body, "实时日志")
        log_card.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.log_text = tk.Text(
            logbody, state="disabled", wrap="word", bd=0, highlightthickness=0,
            bg=COL_LOG_BG, fg=COL_LOG_FG, insertbackground="#ffffff",
            font=("Consolas", 10), padx=10, pady=8,
        )
        log_sb = ttk.Scrollbar(logbody, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")

    def _refresh_main(self):
        self.room_lbl.configure(text=f"直播间: {self.cfg.get('room_id') or '—'}")
        self.name_lbl.configure(text=f"主播: {self.cfg.get('streamer_name') or '—'}")

    # ---------- 动作 ----------
    def _open_author(self):
        try:
            webbrowser.open(AUTHOR_URL)
            self.log(f"[支持] 已打开作者主页: {AUTHOR_URL}")
        except Exception as e:
            self.log(f"[错误] 打开链接失败: {e}")

    def _open_settings(self):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.lift()
            self.settings_win.focus_force()
            return
        self.settings_win = SettingsWindow(self)

    def _start(self):
        if self.controller.start_recording(source="manual"):
            self.log("[手动] 开始录制。")

    def _stop(self):
        self.log("[手动] 停止录制。")
        self.controller.stop_recording()

    def _upload_last(self):
        self.controller.upload_file(
            self.controller.last_recording, title=self.controller.current_title
        )

    def _upload_file(self):
        p = filedialog.askopenfilename(
            title="选择要上传的视频",
            filetypes=[("视频文件", "*.flv *.mp4 *.ts *.mkv"), ("所有文件", "*.*")],
        )
        if p:
            self.controller.upload_file(p)

    # ---------- 轮询 ----------
    def _poll_log(self):
        try:
            while True:
                msg = self.log.queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _poll_status(self):
        if self.controller.recording:
            mb = self.controller.recorder.bytes_written / 1024 / 1024
            self.state_lbl.configure(text="状态: 录制中…", fg=COL_RED)
            self.bytes_lbl.configure(text=f"已写入 {mb:.1f} MB")
        elif self.controller.uploading:
            self.state_lbl.configure(text="状态: 上传中…", fg=COL_ACCENT)
            self.bytes_lbl.configure(text="")
        else:
            self.state_lbl.configure(text="状态: 就绪", fg=COL_GREEN)
            self.bytes_lbl.configure(text="")
        self.btn_start.configure(
            state="disabled" if self.controller.recording else "normal"
        )
        self.btn_stop.configure(
            state="normal" if self.controller.recording else "disabled"
        )
        self.after(300, self._poll_status)

    def _on_close(self):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.collect_and_apply(silent=True)
        self.controller.shutdown()
        self.destroy()


# =========================== 设置窗口 ===========================
class SettingsWindow(tk.Toplevel):
    def __init__(self, app: App):
        super().__init__(app)
        self.app = app
        self.cfg = app.cfg
        self.title("设置")
        self.configure(bg=COL_BG)
        w, h = 580, 720
        self.geometry(f"{w}x{h}")
        self.transient(app)
        self.minsize(520, 480)

        # 变量
        self.room_var = tk.StringVar(value=self.cfg.get("room_id", ""))
        self.name_var = tk.StringVar(value=self.cfg.get("streamer_name", ""))
        self.title_var = tk.StringVar(value=self.cfg.get("title_template", "【{date}录播】{name}的直播回放"))
        self.out_var = tk.StringVar(value=self.cfg.get("output_dir", "") or app.controller.default_output_dir())
        self.backup_var = tk.StringVar(value=self.cfg.get("backup_dir", ""))
        self.retention_var = tk.StringVar(value=str(self.cfg.get("retention_days", 0)))
        self.minfree_var = tk.StringVar(value=str(self.cfg.get("min_free_gb", 20)))
        self.cover_mode_var = tk.StringVar(value=self.cfg.get("cover_mode", "text") or "text")
        self.cover_img_var = tk.StringVar(value=self.cfg.get("cover_image", ""))
        self.sessdata_var = tk.StringVar(value=self.cfg.get("sessdata", ""))
        self.jct_var = tk.StringVar(value=self.cfg.get("bili_jct", ""))
        self.buvid3_var = tk.StringVar(value=self.cfg.get("buvid3", ""))
        self.dede_var = tk.StringVar(value=self.cfg.get("dedeuserid", ""))
        self.tags_var = tk.StringVar(value=self.cfg.get("tags", "录播,直播"))
        self.desc_var = tk.StringVar(value=self.cfg.get("desc", "B站直播录播回放"))

        self.detect_var = tk.BooleanVar(value=bool(self.cfg.get("autodetect_enabled")))
        self.interval_var = tk.StringVar(value=str(self.cfg.get("autodetect_interval", 5)))
        self.schedule_var = tk.BooleanVar(value=bool(self.cfg.get("schedule_enabled")))
        self.sched_start_var = tk.StringVar(value=self.cfg.get("schedule_start", "20:00"))
        self.sched_end_var = tk.StringVar(value=self.cfg.get("schedule_end", "23:00"))
        self.autoupload_var = tk.BooleanVar(value=bool(self.cfg.get("auto_upload", True)))
        self.autostart_var = tk.BooleanVar(value=bool(self.cfg.get("autostart")))
        self.log_var = tk.BooleanVar(value=bool(self.cfg.get("log_enabled", True)))

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._on_cover_mode_change(silent=True)

    # --- 小部件辅助 ---
    def _field(self, parent, label, var, width=32, show=None):
        row = tk.Frame(parent, bg=COL_CARD)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=COL_CARD, fg=COL_TEXT, width=12, anchor="w",
                 font=(UI_FONT, 9)).pack(side="left")
        e = ttk.Entry(row, textvariable=var, width=width, show=show)
        e.pack(side="left", fill="x", expand=True)
        return e

    def _path_field(self, parent, label, var, browse_cmd):
        row = tk.Frame(parent, bg=COL_CARD)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=COL_CARD, fg=COL_TEXT, width=12, anchor="w",
                 font=(UI_FONT, 9)).pack(side="left")
        ttk.Entry(row, textvariable=var, width=30).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="浏览…", command=browse_cmd, relief="flat", bd=0,
                  bg="#e7edf3", fg=COL_TEXT, padx=8, cursor="hand2",
                  font=(UI_FONT, 9)).pack(side="left", padx=(6, 0))

    def _toggle_row(self, parent, text, desc, var):
        row = tk.Frame(parent, bg=COL_CARD)
        row.pack(fill="x", pady=5)
        left = tk.Frame(row, bg=COL_CARD)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=text, bg=COL_CARD, fg=COL_TEXT, anchor="w",
                 font=(UI_FONT, 10)).pack(anchor="w")
        if desc:
            tk.Label(left, text=desc, bg=COL_CARD, fg=COL_MUTED, anchor="w",
                     font=(UI_FONT, 8)).pack(anchor="w")
        ToggleSwitch(row, variable=var, bg=COL_CARD).pack(side="right")

    def _section(self, parent, title):
        outer = tk.Frame(parent, bg=COL_CARD, highlightbackground=COL_BORDER,
                         highlightthickness=1)
        outer.pack(fill="x", padx=12, pady=6)
        tk.Label(outer, text=title, bg=COL_CARD, fg=COL_ACCENT,
                 font=(UI_FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        body = tk.Frame(outer, bg=COL_CARD)
        body.pack(fill="x", padx=14, pady=(0, 12))
        return body

    def _build(self):
        # 底部按钮栏（固定）
        bar = tk.Frame(self, bg=COL_CARD, highlightbackground=COL_BORDER, highlightthickness=1)
        bar.pack(side="bottom", fill="x")
        tk.Button(bar, text="保存", command=self.collect_and_apply, bg=COL_ACCENT, fg="#fff",
                  activebackground=COL_ACCENT2, relief="flat", bd=0, padx=22, pady=8,
                  cursor="hand2", font=(UI_FONT, 10, "bold")).pack(side="right", padx=12, pady=10)
        tk.Button(bar, text="关闭", command=self._on_close, bg="#e7edf3", fg=COL_TEXT,
                  relief="flat", bd=0, padx=22, pady=8, cursor="hand2",
                  font=(UI_FONT, 10)).pack(side="right", pady=10)

        # 滚动区
        outer = tk.Frame(self, bg=COL_BG)
        outer.pack(side="top", fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=COL_BG, highlightthickness=0, bd=0)
        vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")
        holder = tk.Frame(canvas, bg=COL_BG)
        win = canvas.create_window((0, 0), window=holder, anchor="nw")
        holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        # 直播与标题
        s = self._section(holder, "直播与标题")
        self._field(s, "直播间号", self.room_var)
        self._field(s, "主播名", self.name_var)
        self._field(s, "标题模板", self.title_var)
        tk.Label(s, text="{date}=直播日期(自动)  {name}=主播名，其余文字可改",
                 bg=COL_CARD, fg=COL_MUTED, font=(UI_FONT, 8)).pack(anchor="w")

        # 存储与空间
        s = self._section(holder, "存储与空间")
        self._path_field(s, "保存位置", self.out_var, lambda: self._browse_dir(self.out_var))
        self._path_field(s, "备用位置", self.backup_var, lambda: self._browse_dir(self.backup_var))
        r = tk.Frame(s, bg=COL_CARD); r.pack(fill="x", pady=3)
        tk.Label(r, text="保留天数", bg=COL_CARD, fg=COL_TEXT, width=12, anchor="w",
                 font=(UI_FONT, 9)).pack(side="left")
        ttk.Entry(r, textvariable=self.retention_var, width=8).pack(side="left")
        tk.Label(r, text="(0=永久)   空间阈值(GB)", bg=COL_CARD, fg=COL_MUTED,
                 font=(UI_FONT, 9)).pack(side="left", padx=(8, 6))
        ttk.Entry(r, textvariable=self.minfree_var, width=8).pack(side="left")

        # 封面
        s = self._section(holder, "封面")
        rr = tk.Frame(s, bg=COL_CARD); rr.pack(fill="x", pady=3)
        tk.Radiobutton(rr, text="自动文字封面", variable=self.cover_mode_var, value="text",
                       command=self._on_cover_mode_change, bg=COL_CARD, fg=COL_TEXT,
                       activebackground=COL_CARD, selectcolor=COL_CARD,
                       font=(UI_FONT, 9)).pack(side="left")
        tk.Radiobutton(rr, text="自定义图片", variable=self.cover_mode_var, value="image",
                       command=self._on_cover_mode_change, bg=COL_CARD, fg=COL_TEXT,
                       activebackground=COL_CARD, selectcolor=COL_CARD,
                       font=(UI_FONT, 9)).pack(side="left", padx=10)
        row = tk.Frame(s, bg=COL_CARD); row.pack(fill="x", pady=3)
        self.cover_entry = ttk.Entry(row, textvariable=self.cover_img_var)
        self.cover_entry.pack(side="left", fill="x", expand=True)
        tk.Button(row, text="选择图片…", command=self._browse_cover, relief="flat", bd=0,
                  bg="#e7edf3", fg=COL_TEXT, padx=8, cursor="hand2",
                  font=(UI_FONT, 9)).pack(side="left", padx=(6, 0))

        # 投稿账号
        s = self._section(holder, "投稿账号 Cookie")
        self._field(s, "SESSDATA", self.sessdata_var, show="*")
        self._field(s, "bili_jct", self.jct_var, show="*")
        self._field(s, "buvid3", self.buvid3_var)
        self._field(s, "DedeUserID", self.dede_var)
        self._field(s, "标签", self.tags_var)
        self._field(s, "简介", self.desc_var)
        tk.Button(s, text="测试登录", command=self._test_login, bg=COL_GRAY, fg="#fff",
                  activebackground=COL_GRAY2, relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2", font=(UI_FONT, 9)).pack(anchor="w", pady=(6, 0))

        # 自动化
        s = self._section(holder, "自动化")
        self._toggle_row(s, "开播自动录制", "每隔一段时间检测开播，自动开始 / 下播自动停止", self.detect_var)
        r = tk.Frame(s, bg=COL_CARD); r.pack(fill="x", pady=(0, 6))
        tk.Label(r, text="检测间隔(分钟)", bg=COL_CARD, fg=COL_MUTED,
                 font=(UI_FONT, 9)).pack(side="left")
        ttk.Entry(r, textvariable=self.interval_var, width=6).pack(side="left", padx=6)
        self._toggle_row(s, "定时录制", "每天在设定时间段自动开始 / 停止", self.schedule_var)
        r = tk.Frame(s, bg=COL_CARD); r.pack(fill="x", pady=(0, 6))
        tk.Label(r, text="开始", bg=COL_CARD, fg=COL_MUTED, font=(UI_FONT, 9)).pack(side="left")
        ttk.Entry(r, textvariable=self.sched_start_var, width=7).pack(side="left", padx=6)
        tk.Label(r, text="结束", bg=COL_CARD, fg=COL_MUTED, font=(UI_FONT, 9)).pack(side="left")
        ttk.Entry(r, textvariable=self.sched_end_var, width=7).pack(side="left", padx=6)
        self._toggle_row(s, "录制完成后自动投稿", "录播结束后自动上传到 B 站", self.autoupload_var)
        self._toggle_row(s, "开机自启动", "随系统启动，便于自动蹲播", self.autostart_var)
        self._toggle_row(s, "启用日志记录", f"把日志写入磁盘：{self.app.log.log_dir}", self.log_var)

    def _browse_dir(self, var):
        d = filedialog.askdirectory(title="选择目录", parent=self)
        if d:
            var.set(d)

    def _browse_cover(self):
        f = filedialog.askopenfilename(
            title="选择封面图片", parent=self,
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if f:
            self.cover_img_var.set(f)
            self.cover_mode_var.set("image")
            self._on_cover_mode_change()

    def _on_cover_mode_change(self, silent=False):
        state = "normal" if self.cover_mode_var.get() == "image" else "disabled"
        try:
            self.cover_entry.configure(state=state)
        except Exception:
            pass

    def _test_login(self):
        self.collect_and_apply(silent=True)
        self.app.log("[登录] 正在校验 Cookie…")

        def worker():
            uname = check_login(self.cfg)
            if uname:
                self.app.log(f"[登录] 校验成功，当前账号: {uname}")
            else:
                self.app.log("[登录] 校验失败，请检查 SESSDATA / bili_jct 是否有效。")

        threading.Thread(target=worker, daemon=True).start()

    # ---------- 收集 / 应用 ----------
    def collect_and_apply(self, silent=False):
        try:
            retention = int(self.retention_var.get())
        except (TypeError, ValueError):
            retention = 0
        try:
            minfree = float(self.minfree_var.get())
        except (TypeError, ValueError):
            minfree = 20.0
        try:
            interval = int(self.interval_var.get())
        except (TypeError, ValueError):
            interval = 5

        old = dict(self.cfg)
        self.cfg.update({
            "room_id": self.room_var.get().strip(),
            "streamer_name": self.name_var.get().strip(),
            "title_template": self.title_var.get().strip(),
            "output_dir": self.out_var.get().strip(),
            "backup_dir": self.backup_var.get().strip(),
            "retention_days": max(0, retention),
            "min_free_gb": max(0.0, minfree),
            "cover_mode": self.cover_mode_var.get() or "text",
            "cover_image": self.cover_img_var.get().strip(),
            "sessdata": self.sessdata_var.get().strip(),
            "bili_jct": self.jct_var.get().strip(),
            "buvid3": self.buvid3_var.get().strip(),
            "dedeuserid": self.dede_var.get().strip(),
            "tags": self.tags_var.get().strip(),
            "desc": self.desc_var.get().strip(),
            "autodetect_enabled": bool(self.detect_var.get()),
            "autodetect_interval": max(1, interval),
            "schedule_enabled": bool(self.schedule_var.get()),
            "schedule_start": self.sched_start_var.get().strip() or "20:00",
            "schedule_end": self.sched_end_var.get().strip() or "23:00",
            "auto_upload": bool(self.autoupload_var.get()),
            "autostart": bool(self.autostart_var.get()),
            "log_enabled": bool(self.log_var.get()),
        })
        config.save_config(self.cfg)

        # 副作用
        self.app.log.set_enabled(self.cfg["log_enabled"])
        if autostart is not None:
            try:
                autostart.apply(self.cfg["autostart"])
            except Exception as e:
                self.app.log(f"[错误] 设置开机自启动失败: {e}")
        self.app._refresh_main()

        if not silent:
            self._log_changes(old)
            interval = self.cfg["autodetect_interval"]
            if self.cfg["autodetect_enabled"]:
                self.app.log(
                    f"[设置] 开播检测间隔：{interval} 分钟（每 {interval} 分钟检查一次是否开播）"
                )
            else:
                self.app.log("[设置] 开播自动录制：已关闭（不会检测是否开播）")
            self.app.log(
                "[设置] 已保存。自动录制:%s  定时:%s  自动投稿:%s  自启动:%s  日志:%s"
                % (
                    "开" if self.cfg["autodetect_enabled"] else "关",
                    "开" if self.cfg["schedule_enabled"] else "关",
                    "开" if self.cfg["auto_upload"] else "关",
                    "开" if self.cfg["autostart"] else "关",
                    "开" if self.cfg["log_enabled"] else "关",
                )
            )

    def _log_changes(self, old):
        """对比保存前后的配置，输出变更项（debug 风格）。"""
        changes = []

        def onoff(v):
            return "开" if v else "关"

        if old.get("room_id") != self.cfg["room_id"]:
            changes.append(f"直播间号={self.cfg['room_id'] or '空'}")
        if old.get("streamer_name") != self.cfg["streamer_name"]:
            changes.append(f"主播名={self.cfg['streamer_name'] or '空'}")
        if old.get("title_template") != self.cfg["title_template"]:
            changes.append("标题模板已修改")
        if old.get("output_dir") != self.cfg["output_dir"]:
            changes.append(f"保存位置={self.cfg['output_dir'] or '默认'}")
        if old.get("backup_dir") != self.cfg["backup_dir"]:
            changes.append(f"备用位置={self.cfg['backup_dir'] or '无'}")
        if int(old.get("retention_days", 0) or 0) != self.cfg["retention_days"]:
            changes.append(f"保留天数={self.cfg['retention_days']}")
        if float(old.get("min_free_gb", 20) or 0) != self.cfg["min_free_gb"]:
            changes.append(f"空间阈值={self.cfg['min_free_gb']:.0f}GB")
        if (old.get("cover_mode") or "text") != self.cfg["cover_mode"]:
            changes.append(
                "封面=" + ("自定义图片" if self.cfg["cover_mode"] == "image" else "文字封面")
            )
        if bool(old.get("autodetect_enabled")) != self.cfg["autodetect_enabled"]:
            changes.append("开播自动录制=" + onoff(self.cfg["autodetect_enabled"]))
        if int(old.get("autodetect_interval", 5) or 5) != self.cfg["autodetect_interval"]:
            changes.append(f"检测间隔={self.cfg['autodetect_interval']}分钟")
        if bool(old.get("schedule_enabled")) != self.cfg["schedule_enabled"]:
            changes.append("定时录制=" + onoff(self.cfg["schedule_enabled"]))
        if (
            old.get("schedule_start") != self.cfg["schedule_start"]
            or old.get("schedule_end") != self.cfg["schedule_end"]
        ):
            changes.append(
                f"定时时段={self.cfg['schedule_start']}-{self.cfg['schedule_end']}"
            )
        if bool(old.get("auto_upload")) != self.cfg["auto_upload"]:
            changes.append("自动投稿=" + onoff(self.cfg["auto_upload"]))
        if bool(old.get("autostart")) != self.cfg["autostart"]:
            changes.append("开机自启动=" + onoff(self.cfg["autostart"]))
        if bool(old.get("log_enabled")) != self.cfg["log_enabled"]:
            changes.append("日志记录=" + onoff(self.cfg["log_enabled"]))
        if changes:
            self.app.log("[设置] 变更：" + "；".join(changes))

    def _on_close(self):
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
