"""扫码登录对话框：显示二维码、轮询状态、登录成功后回写 Cookie。"""

from bilibili_api.login_v2 import QrCodeLoginEvents
import customtkinter as ctk

from login import EV_DONE, EV_ERROR, EV_QR, EV_STATE, QrLoginSession, STATE_TEXT

from . import theme as T
from .widgets import action_button, ghost_button


class QrLoginDialog(ctk.CTkToplevel):
    """B 站扫码登录窗口。

    on_success(cred: dict) 在登录成功后回调，字典含
    sessdata / bili_jct / buvid3 / dedeuserid / ac_time_value。
    """

    QR_SIZE = 240

    def __init__(self, master, on_success, log=None, on_close=None):
        super().__init__(master)
        self._on_success = on_success
        self._log = log or (lambda msg: None)
        self._on_close_cb = on_close
        self._session = None
        self._img = None
        self._poll_after = None
        self._finished = False

        self.title("扫码登录 B 站")
        self.geometry("380x560")
        self.resizable(False, False)
        self.configure(fg_color=T.BG)
        self.transient(master)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(120, self._start_session)
        # 让窗口出现在前景（CTkToplevel 在部分 Windows 主题下不会自动置顶）
        self.after(200, self._bring_to_front)

    # ---------------- 构建 ----------------
    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="扫码登录", font=T.font(19, "bold"), text_color=T.TEXT
        ).pack(pady=(22, 2))
        ctk.CTkLabel(
            self,
            text="打开 B站 手机客户端 → 我的 → 扫一扫",
            font=T.font(12),
            text_color=T.MUTED,
        ).pack(pady=(0, 14))

        holder = ctk.CTkFrame(
            self,
            fg_color="#ffffff",
            corner_radius=14,
            width=self.QR_SIZE + 28,
            height=self.QR_SIZE + 28,
        )
        holder.pack()
        holder.pack_propagate(False)
        self.qr_label = ctk.CTkLabel(holder, text="二维码生成中…", text_color="#666666")
        self.qr_label.pack(expand=True)

        self.status = ctk.CTkLabel(
            self, text="正在获取二维码…", font=T.font(13), text_color=T.TEXT_DIM
        )
        self.status.pack(pady=(16, 0))

        self.detail = ctk.CTkLabel(
            self,
            text="",
            font=T.font(11),
            text_color=T.MUTED,
            wraplength=320,
            justify="center",
        )
        self.detail.pack(pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=24, pady=20)
        self.refresh_btn = action_button(
            btns, "刷新二维码", self._start_session, width=0, height=38, size=12
        )
        self.refresh_btn.pack(side="left", fill="x", expand=True)
        ghost_button(btns, "关闭", self.close, width=90, height=38, size=12).pack(
            side="left", padx=(10, 0)
        )

    def _bring_to_front(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    # ---------------- 扫码流程 ----------------
    def _start_session(self) -> None:
        if self._finished:
            return
        self._stop_session()
        self._img = None
        self.qr_label.configure(image=None, text="二维码生成中…")
        self.status.configure(text="正在获取二维码…", text_color=T.TEXT_DIM)
        self.detail.configure(text="")
        self.refresh_btn.configure(state="disabled")

        self._session = QrLoginSession(log=self._log)
        self._session.start()
        self._poll()

    def _stop_session(self) -> None:
        if self._poll_after is not None:
            try:
                self.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None
        if self._session is not None:
            self._session.stop()
            self._session = None

    def _poll(self) -> None:
        self._poll_after = None
        if self._session is None or self._finished:
            return
        try:
            while True:
                event = self._session.queue.get_nowait()
                self._handle(event)
        except Exception:
            pass
        if not self._finished:
            self._poll_after = self.after(220, self._poll)

    def _handle(self, event: dict) -> None:
        kind = event.get("type")

        if kind == EV_QR:
            try:
                self._img = ctk.CTkImage(
                    light_image=event["image"],
                    dark_image=event["image"],
                    size=(self.QR_SIZE, self.QR_SIZE),
                )
                self.qr_label.configure(image=self._img, text="")
            except Exception as e:
                self.qr_label.configure(text=f"二维码显示失败\n{e}")
            self.refresh_btn.configure(state="normal")
            self.status.configure(text=STATE_TEXT[QrCodeLoginEvents.SCAN], text_color=T.ACCENT)
            self.detail.configure(text="二维码 3 分钟内有效，过期请点「刷新二维码」")

        elif kind == EV_STATE:
            state = event.get("state")
            if state == QrCodeLoginEvents.SCAN:
                self.status.configure(text=STATE_TEXT[state], text_color=T.ACCENT)
            elif state == QrCodeLoginEvents.CONF:
                self.status.configure(text=STATE_TEXT[state], text_color=T.GREEN)
                self.detail.configure(text="确认后本窗口会自动关闭")
            elif state == QrCodeLoginEvents.TIMEOUT:
                self.status.configure(text="二维码已过期", text_color=T.RED)
                self.detail.configure(text="请点击「刷新二维码」重新获取")
                self.refresh_btn.configure(state="normal")

        elif kind == EV_DONE:
            self._finished = True
            self.status.configure(text="登录成功 ✓", text_color=T.GREEN)
            self.detail.configure(text="正在保存账号信息…")
            try:
                self._on_success(event.get("cred") or {})
            except Exception as e:
                self._log(f"[登录] 保存账号信息失败: {e}")
            self.after(700, self.close)

        elif kind == EV_ERROR:
            self.status.configure(text="登录失败", text_color=T.RED)
            self.detail.configure(text=event.get("msg") or "网络异常，请重试")
            self.refresh_btn.configure(state="normal")

    # ---------------- 关闭 ----------------
    def close(self) -> None:
        self._finished = True
        self._stop_session()
        if self._on_close_cb:
            try:
                self._on_close_cb()
            except Exception:
                pass
        self.destroy()
