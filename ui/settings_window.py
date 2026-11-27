"""设置窗口：左侧分类导航 + 右侧分页表单。"""

import threading
from tkinter import filedialog

import customtkinter as ctk

import config
from uploader import check_login
from version import VERSION

from . import theme as T
from .widgets import (
    action_button,
    card,
    field_row,
    form_hint,
    ghost_button,
    path_row,
    switch_row,
)

try:
    import autostart
except Exception:
    autostart = None


PAGES = (
    ("live", "直播与标题", "⌁"),
    ("storage", "存储与空间", "▤"),
    ("cover", "封面", "▣"),
    ("account", "投稿账号", "◍"),
    ("auto", "自动化", "⏱"),
    ("about", "关于", "ⓘ"),
)


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.cfg = app.cfg
        self.title("设置")
        self.configure(fg_color=T.BG)
        self.geometry("880x640")
        self.minsize(760, 560)
        self.transient(app)

        self._page_frames = {}
        self._nav_buttons = {}
        self._current = None

        self._init_vars()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._on_cover_mode_change(silent=True)
        self._select("live")
        self.after(150, self._bring_to_front)

    # ---------------- 变量 ----------------
    def _init_vars(self) -> None:
        cfg = self.cfg
        self.room_var = ctk.StringVar(value=cfg.get("room_id", ""))
        self.name_var = ctk.StringVar(value=cfg.get("streamer_name", ""))
        self.title_var = ctk.StringVar(
            value=cfg.get("title_template", "【{date}录播】{name}的直播回放")
        )
        self.out_var = ctk.StringVar(
            value=cfg.get("output_dir", "") or self.app.controller.default_output_dir()
        )
        self.backup_var = ctk.StringVar(value=cfg.get("backup_dir", ""))
        self.retention_var = ctk.StringVar(value=str(cfg.get("retention_days", 0)))
        self.minfree_var = ctk.StringVar(value=str(cfg.get("min_free_gb", 20)))
        self.cover_mode_var = ctk.StringVar(value=cfg.get("cover_mode", "text") or "text")
        self.cover_img_var = ctk.StringVar(value=cfg.get("cover_image", ""))
        self.sessdata_var = ctk.StringVar(value=cfg.get("sessdata", ""))
        self.jct_var = ctk.StringVar(value=cfg.get("bili_jct", ""))
        self.buvid3_var = ctk.StringVar(value=cfg.get("buvid3", ""))
        self.dede_var = ctk.StringVar(value=cfg.get("dedeuserid", ""))
        self.tags_var = ctk.StringVar(value=cfg.get("tags", "录播,直播"))
        self.desc_var = ctk.StringVar(value=cfg.get("desc", "B站直播录播回放"))

        self.detect_var = ctk.BooleanVar(value=bool(cfg.get("autodetect_enabled")))
        self.interval_var = ctk.StringVar(value=str(cfg.get("autodetect_interval", 5)))
        self.schedule_var = ctk.BooleanVar(value=bool(cfg.get("schedule_enabled")))
        self.sched_start_var = ctk.StringVar(value=cfg.get("schedule_start", "20:00"))
        self.sched_end_var = ctk.StringVar(value=cfg.get("schedule_end", "23:00"))
        self.autoupload_var = ctk.BooleanVar(value=bool(cfg.get("auto_upload", True)))
        self.autostart_var = ctk.BooleanVar(value=bool(cfg.get("autostart")))
        self.log_var = ctk.BooleanVar(value=bool(cfg.get("log_enabled", True)))
        self.tray_var = ctk.BooleanVar(value=bool(cfg.get("minimize_to_tray", True)))

    # ---------------- 构建 ----------------
    def _bring_to_front(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 左侧导航
        side = ctk.CTkFrame(self, fg_color=T.SIDEBAR, corner_radius=0, width=186)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)

        ctk.CTkLabel(
            side, text="设置", font=T.font(17, "bold"), text_color=T.TEXT, anchor="w"
        ).pack(fill="x", padx=20, pady=(24, 16))

        for key, label, icon in PAGES:
            btn = ctk.CTkButton(
                side,
                text=f"{icon}   {label}",
                anchor="w",
                command=lambda k=key: self._select(k),
                fg_color="transparent",
                hover_color=T.CARD_HOVER,
                text_color=T.TEXT_DIM,
                corner_radius=9,
                height=38,
                font=T.font(13),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = btn

        ctk.CTkLabel(
            side, text=f"v{VERSION}", font=T.font(11), text_color=T.MUTED
        ).pack(side="bottom", pady=16)

        # 右侧内容区 + 底部按钮栏
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.content = ctk.CTkFrame(right, fg_color="transparent")
        self.content.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=(16, 0))

        bar = ctk.CTkFrame(right, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=(12, 8), pady=12)
        action_button(bar, "保存", self.collect_and_apply, width=120, height=40).pack(
            side="right"
        )
        ghost_button(bar, "关闭", self._on_close, width=96, height=40).pack(
            side="right", padx=(0, 10)
        )

        self._page_live()
        self._page_storage()
        self._page_cover()
        self._page_account()
        self._page_auto()
        self._page_about()

    def _new_page(self, key: str) -> ctk.CTkScrollableFrame:
        frame = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=T.CARD_HOVER,
            scrollbar_button_hover_color=T.GRAY,
        )
        self._page_frames[key] = frame
        return frame

    def _section(self, parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
        c = card(parent)
        c.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            c, text=title, font=T.font(14, "bold"), text_color=T.TEXT, anchor="w"
        ).pack(anchor="w", padx=18, pady=(16, 0))
        if subtitle:
            ctk.CTkLabel(
                c, text=subtitle, font=T.font(11), text_color=T.MUTED, anchor="w"
            ).pack(anchor="w", padx=18, pady=(1, 0))
        body = ctk.CTkFrame(c, fg_color="transparent")
        body.pack(fill="x", padx=0, pady=(10, 16))
        return body

    # ---------------- 各分页 ----------------
    def _page_live(self) -> None:
        page = self._new_page("live")
        body = self._section(page, "直播与标题", "录制哪个直播间，以及投稿标题怎么生成")
        field_row(body, "直播间号", self.room_var, placeholder="例如 21452505")
        field_row(body, "主播名", self.name_var, placeholder="留空则显示「主播」")
        field_row(body, "标题模板", self.title_var)
        form_hint(
            body,
            "{date} = 直播日期（开播日期，自动替换）    {name} = 主播名\n"
            "其余文字可以自由修改，例如：【{date}录播】{name}的直播回放",
        )

    def _page_storage(self) -> None:
        page = self._new_page("storage")
        body = self._section(page, "保存位置", "录播文件的落盘位置，空间不足时会自动切换")
        path_row(body, "保存位置", self.out_var, lambda: self._browse_dir(self.out_var))
        path_row(body, "备用位置", self.backup_var, lambda: self._browse_dir(self.backup_var))

        body2 = self._section(page, "空间与清理", "避免录播把硬盘塞满")
        row = ctk.CTkFrame(body2, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(
            row, text="保留天数", width=92, anchor="w",
            font=T.font(12), text_color=T.TEXT_DIM,
        ).pack(side="left")
        ctk.CTkEntry(
            row, textvariable=self.retention_var, width=70, height=34,
            fg_color=T.BG, border_color=T.BORDER, text_color=T.TEXT, corner_radius=8,
        ).pack(side="left")
        ctk.CTkLabel(
            row, text=" 天（0 = 永久保留）", font=T.font(11), text_color=T.MUTED
        ).pack(side="left")
        ctk.CTkLabel(
            row, text="空间阈值", width=92, anchor="w",
            font=T.font(12), text_color=T.TEXT_DIM,
        ).pack(side="left", padx=(24, 0))
        ctk.CTkEntry(
            row, textvariable=self.minfree_var, width=70, height=34,
            fg_color=T.BG, border_color=T.BORDER, text_color=T.TEXT, corner_radius=8,
        ).pack(side="left")
        ctk.CTkLabel(
            row, text=" GB", font=T.font(11), text_color=T.MUTED
        ).pack(side="left")
        form_hint(
            body2,
            "剩余空间低于阈值时切换到备用位置；两个位置都不足时，自动删除最早三天的录播腾空间。",
        )

    def _page_cover(self) -> None:
        page = self._new_page("cover")
        body = self._section(page, "投稿封面", "不选图片就用标题自动生成一张文字封面")
        radios = ctk.CTkFrame(body, fg_color="transparent")
        radios.pack(fill="x", padx=18, pady=(0, 6))
        ctk.CTkRadioButton(
            radios, text="自动文字封面", variable=self.cover_mode_var, value="text",
            command=self._on_cover_mode_change, fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER, text_color=T.TEXT, font=T.font(12),
        ).pack(side="left")
        ctk.CTkRadioButton(
            radios, text="自定义图片", variable=self.cover_mode_var, value="image",
            command=self._on_cover_mode_change, fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER, text_color=T.TEXT, font=T.font(12),
        ).pack(side="left", padx=(18, 0))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=6)
        self.cover_entry = ctk.CTkEntry(
            row, textvariable=self.cover_img_var, height=34, fg_color=T.BG,
            border_color=T.BORDER, text_color=T.TEXT, corner_radius=8,
            placeholder_text="选择一张图片…",
        )
        self.cover_entry.pack(side="left", fill="x", expand=True)
        ghost_button(row, "选择图片…", self._browse_cover, width=96, height=34).pack(
            side="left", padx=(8, 0)
        )
        form_hint(body, "图片会按 16:9 居中裁剪并缩放到 1920×1080 再上传。")

    def _page_account(self) -> None:
        page = self._new_page("account")
        body = self._section(page, "登录状态", "推荐直接扫码登录，无需手动抓 Cookie")
        self.account_lbl = ctk.CTkLabel(
            body, text="", font=T.font(12), text_color=T.MUTED, anchor="w"
        )
        self.account_lbl.pack(fill="x", padx=18, pady=(0, 8))
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", padx=18)
        action_button(row, "扫码登录", self.app._open_login, height=38, size=13).pack(
            side="left"
        )
        ghost_button(row, "测试登录", self._test_login, width=96, height=38).pack(
            side="left", padx=(8, 0)
        )
        self._refresh_account_label()

        body2 = self._section(
            page, "投稿参数", "标签用英文逗号分隔，最多 10 个"
        )
        field_row(body2, "标签", self.tags_var, placeholder="录播,直播")
        field_row(body2, "简介", self.desc_var, placeholder="B站直播录播回放")

        body3 = self._section(
            page, "手动 Cookie（高级）", "扫码登录会自动填好这些，一般不需要手改"
        )
        field_row(body3, "SESSDATA", self.sessdata_var, show="*")
        field_row(body3, "bili_jct", self.jct_var, show="*")
        field_row(body3, "buvid3", self.buvid3_var)
        field_row(body3, "DedeUserID", self.dede_var)

    def _page_auto(self) -> None:
        page = self._new_page("auto")
        body = self._section(page, "开播检测", "定时检测直播间状态，开播自动开始、下播自动停止")
        switch_row(
            body, "开播自动录制", "关闭后不会检测开播，只能在主界面手动开始", self.detect_var
        )
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 6))
        ctk.CTkLabel(
            row, text="检测间隔", width=92, anchor="w",
            font=T.font(12), text_color=T.TEXT_DIM,
        ).pack(side="left")
        ctk.CTkEntry(
            row, textvariable=self.interval_var, width=70, height=34,
            fg_color=T.BG, border_color=T.BORDER, text_color=T.TEXT, corner_radius=8,
        ).pack(side="left")
        ctk.CTkLabel(row, text=" 分钟", font=T.font(11), text_color=T.MUTED).pack(side="left")

        body2 = self._section(page, "定时任务", "每天在固定时间段录制，适合规律开播的主播")
        switch_row(body2, "定时录制", "到点自动开始 / 结束", self.schedule_var)
        row = ctk.CTkFrame(body2, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 6))
        for label, var in (("开始", self.sched_start_var), ("结束", self.sched_end_var)):
            ctk.CTkLabel(
                row, text=label, width=44, anchor="w", font=T.font(12), text_color=T.TEXT_DIM
            ).pack(side="left")
            ctk.CTkEntry(
                row, textvariable=var, width=76, height=34, fg_color=T.BG,
                border_color=T.BORDER, text_color=T.TEXT, corner_radius=8,
            ).pack(side="left", padx=(0, 18))
        ctk.CTkLabel(
            row, text="格式 HH:MM，例如 20:00", font=T.font(11), text_color=T.MUTED
        ).pack(side="left")

        body3 = self._section(page, "其他", "")
        switch_row(body3, "录制完成后自动投稿", "录播结束后自动上传到 B 站", self.autoupload_var)
        switch_row(body3, "开机自启动", "随系统启动，便于自动蹲播", self.autostart_var)
        switch_row(
            body3, "启用日志记录", f"日志目录：{self.app.log.log_dir}", self.log_var
        )
        switch_row(
            body3,
            "关闭时最小化到托盘",
            "点窗口右上角关闭不退出程序，缩到系统托盘继续录制 / 蹲播；右键托盘图标可退出",
            self.tray_var,
        )

    def _page_about(self) -> None:
        page = self._new_page("about")
        body = self._section(page, "关于", f"B站直播录播 + 自动投稿  v{VERSION}")
        info = (
            "录制：streamlink 抓取原画流，断线自动重连（最多 3 次）\n"
            "投稿：bilibili-api-python，支持自定义标题模板 / 封面 / 标签\n"
            "登录：B站 手机客户端扫码，自动保存 Cookie"
        )
        ctk.CTkLabel(
            body, text=info, font=T.font(12), text_color=T.TEXT_DIM,
            justify="left", anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 10))
        action_button(
            body, "❤ 打开作者主页", self.app._open_author,
            color=T.PINK, hover=T.PINK_HOVER, width=160, height=38, size=12,
        ).pack(anchor="w", padx=18)
        form_hint(
            body,
            f"配置文件：{config.CONFIG_PATH}\n日志目录：{self.app.log.log_dir}",
        )

    # ---------------- 交互 ----------------
    def _select(self, key: str) -> None:
        if self._current == key:
            return
        for k, frame in self._page_frames.items():
            if k == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=T.CARD, text_color=T.TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEXT_DIM)
        self._current = key

    def _browse_dir(self, var) -> None:
        d = filedialog.askdirectory(title="选择目录", parent=self)
        if d:
            var.set(d)

    def _browse_cover(self) -> None:
        f = filedialog.askopenfilename(
            title="选择封面图片", parent=self,
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if f:
            self.cover_img_var.set(f)
            self.cover_mode_var.set("image")
            self._on_cover_mode_change()

    def _on_cover_mode_change(self, silent: bool = False) -> None:
        state = "normal" if self.cover_mode_var.get() == "image" else "disabled"
        try:
            self.cover_entry.configure(state=state)
        except Exception:
            pass

    def _test_login(self) -> None:
        self.collect_and_apply(silent=True)
        self.app.log("[登录] 正在校验 Cookie…")

        def worker():
            uname = check_login(self.cfg)
            if uname:
                self.app.log(f"[登录] 校验成功，当前账号: {uname}")
            else:
                self.app.log("[登录] 校验失败，请点「扫码登录」重新登录。")
            self.app._post(lambda: self._refresh_account_label(uname))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_account_label(self, uname=None) -> None:
        try:
            if uname:
                text, color = f"已登录：{uname}", T.GREEN
            elif str(self.cfg.get("sessdata", "")).strip():
                text, color = "已保存 Cookie（点「测试登录」可校验）", T.TEXT_DIM
            else:
                text, color = "未登录，投稿前请先扫码登录", T.MUTED
            self.account_lbl.configure(text=text, text_color=color)
        except Exception:
            pass

    # ---------------- 同步 / 收集 ----------------
    def sync_from_config(self) -> None:
        """扫码登录后用配置刷新输入框。"""
        self.sessdata_var.set(self.cfg.get("sessdata", ""))
        self.jct_var.set(self.cfg.get("bili_jct", ""))
        self.buvid3_var.set(self.cfg.get("buvid3", ""))
        self.dede_var.set(self.cfg.get("dedeuserid", ""))
        self._refresh_account_label()

    def collect_and_apply(self, silent: bool = False) -> None:
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
            "minimize_to_tray": bool(self.tray_var.get()),
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
        self._refresh_account_label()

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

    def _log_changes(self, old: dict) -> None:
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
        if bool(old.get("minimize_to_tray", True)) != self.cfg["minimize_to_tray"]:
            changes.append("关闭缩托盘=" + onoff(self.cfg["minimize_to_tray"]))
        if changes:
            self.app.log("[设置] 变更：" + "；".join(changes))

    def _on_close(self) -> None:
        self.destroy()
