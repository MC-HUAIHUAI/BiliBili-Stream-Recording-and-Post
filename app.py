"""B 站直播录播 + 自动投稿工具 —— tkinter GUI 入口"""

import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import config
import utils
from recorder import Recorder
from scheduler import Scheduler
from uploader import BiliUploader, check_login

APP_TITLE = "B站直播录播 + 自动投稿"
VERSION = "1.4.1"


class Logger:
    """线程安全日志队列。"""

    def __init__(self):
        self.queue = queue.Queue()

    def __call__(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.queue.put(f"[{ts}] {msg}")


class Controller:
    """录制/上传/调度的控制中心。"""

    def __init__(self, log: Logger):
        self.log = log
        self.cfg = config.load_config()
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
        """按剩余空间选择保存位置；都不足时删除最早三天录播。返回最终目录。"""
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
            self.log("[错误] 请先填写直播间号。")
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{VERSION}")

        self.log = Logger()
        self.controller = Controller(self.log)
        self.cfg = self.controller.cfg
        self._loading = False

        self._build_style()
        self._build_widgets()
        self._load_cfg_to_widgets()

        self.update_idletasks()
        win_h = min(self.winfo_reqheight(), self.winfo_screenheight() - 80)
        self.geometry(f"780x{win_h}")
        self.minsize(720, min(820, win_h))

        self.controller.scheduler.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_log)
        self.after(300, self._poll_status)
        threading.Thread(target=self.controller.cleanup_old_recordings, daemon=True).start()

    # ---------- UI 构建 ----------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            pass
        style.configure("Title.TLabel", font=("Microsoft YaHei", 14, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Microsoft YaHei", 10, "bold"))

    def _build_widgets(self):
        pad = {"padx": 6, "pady": 4}

        tk.Label(self, text=f"{APP_TITLE} v{VERSION}", font=("Microsoft YaHei", 15, "bold")).pack(
            pady=(10, 4)
        )

        # ---- 录播设置 ----
        rec = ttk.LabelFrame(self, text="录播设置", style="Section.TLabelframe")
        rec.pack(fill="x", padx=10, pady=6)

        ttk.Label(rec, text="直播间号:").grid(row=0, column=0, sticky="e", **pad)
        self.room_var = tk.StringVar()
        self.room_entry = ttk.Entry(rec, textvariable=self.room_var, width=24)
        self.room_entry.grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(rec, text="主播名:").grid(row=0, column=2, sticky="e", **pad)
        self.name_var = tk.StringVar()
        ttk.Entry(rec, textvariable=self.name_var, width=16).grid(
            row=0, column=3, sticky="w", **pad
        )

        ttk.Label(rec, text="输出画质:").grid(row=1, column=0, sticky="e", **pad)
        ttk.Label(rec, text="原画 1080p").grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(rec, text="标题模板:").grid(row=1, column=2, sticky="e", **pad)
        self.title_tpl_var = tk.StringVar()
        ttk.Entry(rec, textvariable=self.title_tpl_var, width=24).grid(
            row=1, column=3, sticky="w", **pad
        )
        ttk.Label(
            rec,
            text="提示: {date}=直播日期(自动)  {name}=主播名，其余文字(如“的直播回放”)可自由修改。",
            foreground="#888",
        ).grid(row=2, column=1, columnspan=3, sticky="w", padx=6, pady=(0, 2))

        ttk.Label(rec, text="保存位置:").grid(row=3, column=0, sticky="e", **pad)
        self.outdir_var = tk.StringVar()
        self.outdir_entry = ttk.Entry(rec, textvariable=self.outdir_var, width=34)
        self.outdir_entry.grid(row=3, column=1, columnspan=2, sticky="we", **pad)
        ttk.Button(rec, text="浏览…", command=self._browse_outdir).grid(
            row=3, column=3, sticky="w", **pad
        )

        ttk.Label(rec, text="备用保存位置:").grid(row=4, column=0, sticky="e", **pad)
        self.backup_var = tk.StringVar()
        self.backup_entry = ttk.Entry(rec, textvariable=self.backup_var, width=34)
        self.backup_entry.grid(row=4, column=1, columnspan=2, sticky="we", **pad)
        ttk.Button(rec, text="浏览…", command=self._browse_backup).grid(
            row=4, column=3, sticky="w", **pad
        )

        ttk.Label(rec, text="保留天数(0=永久):").grid(row=5, column=0, sticky="e", **pad)
        self.retention_var = tk.StringVar()
        ttk.Entry(rec, textvariable=self.retention_var, width=8).grid(
            row=5, column=1, sticky="w", **pad
        )
        ttk.Label(rec, text="空间阈值(GB):").grid(row=5, column=2, sticky="e", **pad)
        self.minfree_var = tk.StringVar()
        ttk.Entry(rec, textvariable=self.minfree_var, width=8).grid(
            row=5, column=3, sticky="w", **pad
        )

        ttk.Label(rec, text="标签:").grid(row=6, column=0, sticky="e", **pad)
        self.tags_var = tk.StringVar()
        ttk.Entry(rec, textvariable=self.tags_var, width=34).grid(
            row=6, column=1, columnspan=2, sticky="we", **pad
        )

        ttk.Label(rec, text="简介:").grid(row=7, column=0, sticky="e", **pad)
        self.desc_var = tk.StringVar()
        ttk.Entry(rec, textvariable=self.desc_var, width=34).grid(
            row=7, column=1, columnspan=2, sticky="we", **pad
        )

        rec.columnconfigure(1, weight=1)

        # ---- 封面设置 ----
        cover = ttk.LabelFrame(self, text="封面设置", style="Section.TLabelframe")
        cover.pack(fill="x", padx=10, pady=6)

        self.cover_mode_var = tk.StringVar(value="text")
        self.cover_image_var = tk.StringVar()
        ttk.Radiobutton(
            cover,
            text="自动文字封面（含标题）",
            variable=self.cover_mode_var,
            value="text",
            command=self._on_cover_mode_change,
        ).grid(row=0, column=0, sticky="w", **pad)
        ttk.Radiobutton(
            cover,
            text="自定义图片",
            variable=self.cover_mode_var,
            value="image",
            command=self._on_cover_mode_change,
        ).grid(row=0, column=1, sticky="w", **pad)

        self.cover_entry = ttk.Entry(cover, textvariable=self.cover_image_var, width=42)
        self.cover_entry.grid(row=1, column=0, columnspan=3, sticky="we", **pad)
        ttk.Button(cover, text="浏览图片…", command=self._browse_cover).grid(
            row=1, column=3, sticky="w", **pad
        )
        cover.columnconfigure(0, weight=1)

        # ---- 上传账号 Cookie ----
        up = ttk.LabelFrame(self, text="上传账号 Cookie（B站投稿）", style="Section.TLabelframe")
        up.pack(fill="x", padx=10, pady=6)

        self.sessdata_var = tk.StringVar()
        self.jct_var = tk.StringVar()
        self.buvid3_var = tk.StringVar()
        self.dedeuserid_var = tk.StringVar()

        ttk.Label(up, text="SESSDATA:").grid(row=0, column=0, sticky="e", **pad)
        ttk.Entry(up, textvariable=self.sessdata_var, width=42, show="*").grid(
            row=0, column=1, columnspan=3, sticky="we", **pad
        )
        ttk.Label(up, text="bili_jct:").grid(row=1, column=0, sticky="e", **pad)
        ttk.Entry(up, textvariable=self.jct_var, width=42, show="*").grid(
            row=1, column=1, columnspan=3, sticky="we", **pad
        )
        ttk.Label(up, text="buvid3:").grid(row=2, column=0, sticky="e", **pad)
        ttk.Entry(up, textvariable=self.buvid3_var, width=42).grid(
            row=2, column=1, columnspan=3, sticky="we", **pad
        )
        ttk.Label(up, text="DedeUserID:").grid(row=3, column=0, sticky="e", **pad)
        ttk.Entry(up, textvariable=self.dedeuserid_var, width=42).grid(
            row=3, column=1, columnspan=3, sticky="we", **pad
        )
        ttk.Button(up, text="测试登录", command=self._test_login).grid(
            row=4, column=1, sticky="w", **pad
        )
        ttk.Label(
            up,
            text="提示: 登录 bilibili.com 后按 F12 在 Cookie 中复制对应字段（SESSDATA / bili_jct 必填）。",
            foreground="#888",
        ).grid(row=4, column=1, columnspan=3, sticky="w", padx=(96, 6), pady=4)
        up.columnconfigure(1, weight=1)

        # ---- 自动化 ----
        auto = ttk.LabelFrame(self, text="自动化（定时 / 开播检测）", style="Section.TLabelframe")
        auto.pack(fill="x", padx=10, pady=6)

        self.schedule_var = tk.BooleanVar()
        self.sched_start_var = tk.StringVar()
        self.sched_end_var = tk.StringVar()
        ttk.Checkbutton(auto, text="定时录制", variable=self.schedule_var).grid(
            row=0, column=0, sticky="w", **pad
        )
        ttk.Entry(auto, textvariable=self.sched_start_var, width=8).grid(
            row=0, column=1, **pad
        )
        ttk.Label(auto, text="—").grid(row=0, column=2)
        ttk.Entry(auto, textvariable=self.sched_end_var, width=8).grid(
            row=0, column=3, **pad
        )

        self.detect_var = tk.BooleanVar()
        self.detect_interval_var = tk.StringVar()
        ttk.Checkbutton(auto, text="开播自动录制", variable=self.detect_var).grid(
            row=1, column=0, sticky="w", **pad
        )
        ttk.Label(auto, text="检测间隔(分钟):").grid(row=1, column=1, columnspan=2, sticky="e", **pad)
        ttk.Entry(auto, textvariable=self.detect_interval_var, width=8).grid(
            row=1, column=3, sticky="w", **pad
        )

        self.auto_upload_var = tk.BooleanVar()
        ttk.Checkbutton(auto, text="录制完成后自动投稿", variable=self.auto_upload_var).grid(
            row=2, column=0, columnspan=3, sticky="w", **pad
        )

        # ---- 控制按钮 ----
        ctl = ttk.Frame(self)
        ctl.pack(fill="x", padx=10, pady=6)

        self.btn_start = ttk.Button(ctl, text="开始录制", command=self._start)
        self.btn_start.pack(side="left", padx=4)
        self.btn_stop = ttk.Button(ctl, text="停止录制", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        self.btn_upload = ttk.Button(ctl, text="上传上次录播", command=self._upload_last)
        self.btn_upload.pack(side="left", padx=4)
        self.btn_upload_file = ttk.Button(ctl, text="上传本地文件…", command=self._upload_file)
        self.btn_upload_file.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="状态: 就绪")
        ttk.Label(self, textvariable=self.status_var).pack(anchor="w", padx=12, pady=(4, 0))

        # ---- 日志 ----
        logf = ttk.LabelFrame(self, text="日志", style="Section.TLabelframe")
        logf.pack(fill="both", expand=True, padx=10, pady=6)
        self.log_text = tk.Text(logf, height=8, state="disabled", wrap="word",
                                font=("Consolas", 9))
        sb = ttk.Scrollbar(logf, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._register_traces()

    # ---------- 选项变更日志（debug 风格） ----------
    def _register_traces(self):
        self.schedule_var.trace_add("write", lambda *a: self._on_schedule_change())
        self.detect_var.trace_add("write", lambda *a: self._on_detect_change())
        self.auto_upload_var.trace_add("write", lambda *a: self._on_autoupload_change())
        self.retention_var.trace_add("write", lambda *a: self._on_retention_change())
        self.minfree_var.trace_add("write", lambda *a: self._on_minfree_change())
        self.detect_interval_var.trace_add("write", lambda *a: self._on_interval_change())
        self.room_entry.bind("<FocusOut>", lambda e: self._on_room_change())
        self.outdir_entry.bind("<FocusOut>", lambda e: self._on_outdir_change())
        self.backup_entry.bind("<FocusOut>", lambda e: self._on_backup_change())

    def _on_schedule_change(self):
        if self._loading:
            return
        if self.schedule_var.get():
            self.log(
                f"[设置] 定时录制已开启：每天 {self.sched_start_var.get()} - {self.sched_end_var.get()} 自动开始/停止录制"
            )
        else:
            self.log("[设置] 定时录制已关闭")

    def _on_detect_change(self):
        if self._loading:
            return
        if self.detect_var.get():
            self.log(
                f"[设置] 开播自动录制已开启：每 {self.detect_interval_var.get()} 分钟检测一次，开播自动录制、下播自动停止"
            )
        else:
            self.log("[设置] 开播自动录制已关闭")

    def _on_autoupload_change(self):
        if self._loading:
            return
        if self.auto_upload_var.get():
            self.log("[设置] 自动投稿已开启：录制完成后将自动投稿到 B 站")
        else:
            self.log("[设置] 自动投稿已关闭：录制完成后不会自动上传")

    def _on_retention_change(self):
        if self._loading:
            return
        try:
            d = int(self.retention_var.get())
        except (TypeError, ValueError):
            return
        if d <= 0:
            self.log("[设置] 保留天数设为 0：录播永久保留，不自动删除")
        else:
            self.log(f"[设置] 保留天数设为 {d} 天：超过 {d} 天的录播将自动删除")

    def _on_interval_change(self):
        if self._loading:
            return
        try:
            n = int(self.detect_interval_var.get())
        except (TypeError, ValueError):
            return
        self.log(f"[设置] 开播检测间隔改为: {n} 分钟")

    def _on_room_change(self):
        if self._loading:
            return
        v = self.room_var.get().strip()
        if v:
            self.log(f"[设置] 直播间号改为: {v}（录播与开播检测将针对该直播间）")

    def _on_outdir_change(self):
        if self._loading:
            return
        v = self.outdir_var.get().strip()
        if v:
            self.log(f"[设置] 保存位置改为: {v}")

    def _on_backup_change(self):
        if self._loading:
            return
        v = self.backup_var.get().strip()
        if v:
            self.log(f"[设置] 备用保存位置设为: {v}（主位置空间不足时使用）")
        else:
            self.log("[设置] 备用保存位置已清空")

    def _on_minfree_change(self):
        if self._loading:
            return
        try:
            v = float(self.minfree_var.get())
        except (TypeError, ValueError):
            return
        self.log(f"[设置] 空间阈值设为 {v:.0f} GB：剩余低于该值时切换备用位置、仍不足则删除最早三天录播")

    # ---------- 配置读写 ----------
    def _load_cfg_to_widgets(self):
        self._loading = True
        try:
            self._load_cfg_values()
        finally:
            self._loading = False

    def _load_cfg_values(self):
        self.room_var.set(self.cfg.get("room_id", ""))
        self.name_var.set(self.cfg.get("streamer_name", ""))
        self.title_tpl_var.set(self.cfg.get("title_template", "【{date}录播】{name}的直播回放"))
        self.outdir_var.set(self.cfg.get("output_dir", "") or self.controller.default_output_dir())
        self.backup_var.set(self.cfg.get("backup_dir", ""))
        self.retention_var.set(str(self.cfg.get("retention_days", 0)))
        self.minfree_var.set(str(self.cfg.get("min_free_gb", 20)))
        self.tags_var.set(self.cfg.get("tags", "录播,直播"))
        self.desc_var.set(self.cfg.get("desc", "B站直播录播回放"))
        self.sessdata_var.set(self.cfg.get("sessdata", ""))
        self.jct_var.set(self.cfg.get("bili_jct", ""))
        self.buvid3_var.set(self.cfg.get("buvid3", ""))
        self.dedeuserid_var.set(self.cfg.get("dedeuserid", ""))
        self.schedule_var.set(bool(self.cfg.get("schedule_enabled")))
        self.sched_start_var.set(self.cfg.get("schedule_start", "20:00"))
        self.sched_end_var.set(self.cfg.get("schedule_end", "23:00"))
        self.detect_var.set(bool(self.cfg.get("autodetect_enabled")))
        self.detect_interval_var.set(str(self.cfg.get("autodetect_interval", 5)))
        self.auto_upload_var.set(bool(self.cfg.get("auto_upload", True)))
        self.cover_mode_var.set(self.cfg.get("cover_mode", "text") or "text")
        self.cover_image_var.set(self.cfg.get("cover_image", ""))
        self._on_cover_mode_change()

    def _collect_config(self):
        self.cfg["room_id"] = self.room_var.get().strip()
        self.cfg["streamer_name"] = self.name_var.get().strip()
        self.cfg["title_template"] = self.title_tpl_var.get().strip()
        self.cfg["output_dir"] = self.outdir_var.get().strip()
        self.cfg["backup_dir"] = self.backup_var.get().strip()
        try:
            self.cfg["retention_days"] = int(self.retention_var.get())
        except (TypeError, ValueError):
            self.cfg["retention_days"] = 0
        if self.cfg["retention_days"] < 0:
            self.cfg["retention_days"] = 0
        try:
            self.cfg["min_free_gb"] = float(self.minfree_var.get())
        except (TypeError, ValueError):
            self.cfg["min_free_gb"] = 20.0
        if self.cfg["min_free_gb"] < 0:
            self.cfg["min_free_gb"] = 0.0
        self.cfg["cover_mode"] = self.cover_mode_var.get() or "text"
        self.cfg["cover_image"] = self.cover_image_var.get().strip()
        self.cfg["tags"] = self.tags_var.get().strip()
        self.cfg["desc"] = self.desc_var.get().strip()
        self.cfg["sessdata"] = self.sessdata_var.get().strip()
        self.cfg["bili_jct"] = self.jct_var.get().strip()
        self.cfg["buvid3"] = self.buvid3_var.get().strip()
        self.cfg["dedeuserid"] = self.dedeuserid_var.get().strip()
        self.cfg["schedule_enabled"] = bool(self.schedule_var.get())
        self.cfg["schedule_start"] = self.sched_start_var.get().strip() or "20:00"
        self.cfg["schedule_end"] = self.sched_end_var.get().strip() or "23:00"
        self.cfg["autodetect_enabled"] = bool(self.detect_var.get())
        try:
            self.cfg["autodetect_interval"] = int(self.detect_interval_var.get())
        except (TypeError, ValueError):
            self.cfg["autodetect_interval"] = 5
        self.cfg["auto_upload"] = bool(self.auto_upload_var.get())
        config.save_config(self.cfg)

    # ---------- 动作 ----------
    def _browse_outdir(self):
        d = filedialog.askdirectory(title="选择保存位置")
        if d:
            self.outdir_var.set(d)

    def _browse_backup(self):
        d = filedialog.askdirectory(title="选择备用保存位置")
        if d:
            self.backup_var.set(d)
            self.log(f"[设置] 备用保存位置设为: {d}")

    def _browse_cover(self):
        f = filedialog.askopenfilename(
            title="选择封面图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if f:
            self.cover_image_var.set(f)
            self.cover_mode_var.set("image")
            self._on_cover_mode_change()

    def _on_cover_mode_change(self):
        mode = self.cover_mode_var.get() or "text"
        state = "normal" if mode == "image" else "disabled"
        try:
            self.cover_entry.configure(state=state)
        except Exception:
            pass
        if self._loading:
            return
        if mode == "image":
            self.log("[设置] 封面使用自定义图片")
        else:
            self.log("[设置] 封面使用自动文字封面")

    def _start(self):
        self._collect_config()
        if self.controller.start_recording(source="manual"):
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.status_var.set("状态: 录制中…")

    def _stop(self):
        self.controller.stop_recording()

    def _upload_last(self):
        self._collect_config()
        self.controller.upload_file(
            self.controller.last_recording, title=self.controller.current_title
        )

    def _upload_file(self):
        self._collect_config()
        p = filedialog.askopenfilename(
            title="选择要上传的视频",
            filetypes=[("视频文件", "*.flv *.mp4 *.ts *.mkv"), ("所有文件", "*.*")],
        )
        if p:
            self.controller.upload_file(p)

    def _test_login(self):
        self._collect_config()
        self.log("[登录] 正在校验 Cookie…")

        def worker():
            uname = check_login(self.cfg)
            if uname:
                self.log(f"[登录] 校验成功，当前账号: {uname}")
            else:
                self.log("[登录] 校验失败，请检查 SESSDATA / bili_jct 是否有效。")

        threading.Thread(target=worker, daemon=True).start()

    # ---------- 日志与状态轮询 ----------
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
            self.status_var.set(f"状态: 录制中… 已写入 {mb:.1f} MB")
        elif self.controller.uploading:
            self.status_var.set("状态: 上传中…")
        else:
            self.status_var.set("状态: 就绪")

        self.btn_start.configure(
            state="disabled" if self.controller.recording else "normal"
        )
        self.btn_stop.configure(
            state="normal" if self.controller.recording else "disabled"
        )
        self.after(300, self._poll_status)

    def _on_close(self):
        self._collect_config()
        self.controller.shutdown()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
