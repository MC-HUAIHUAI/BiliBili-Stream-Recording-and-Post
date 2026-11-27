"""可复用的界面组件：卡片、按钮、表单行、开关行等。"""

import customtkinter as ctk

from . import theme as T


def card(master, **kwargs) -> ctk.CTkFrame:
    """统一的卡片容器。"""
    opts = dict(
        fg_color=T.CARD,
        corner_radius=T.CARD_RADIUS,
        border_width=1,
        border_color=T.BORDER,
    )
    opts.update(kwargs)
    return ctk.CTkFrame(master, **opts)


def card_title(master, text: str, subtitle: str = None) -> ctk.CTkLabel:
    """卡片标题（可选副标题两行）。"""
    if subtitle:
        wrap = ctk.CTkFrame(master, fg_color="transparent")
        wrap.pack(fill="x", padx=18, pady=(16, 0))
        ctk.CTkLabel(
            wrap, text=text, font=T.font(14, "bold"), text_color=T.TEXT, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            wrap, text=subtitle, font=T.font(11), text_color=T.MUTED, anchor="w"
        ).pack(anchor="w", pady=(1, 0))
        return wrap
    lbl = ctk.CTkLabel(master, text=text, font=T.font(14, "bold"), text_color=T.TEXT, anchor="w")
    lbl.pack(anchor="w", padx=18, pady=(16, 0))
    return lbl


def divider(master, padx: int = 18, pady: int = 12) -> ctk.CTkFrame:
    line = ctk.CTkFrame(master, height=1, fg_color=T.BORDER)
    line.pack(fill="x", padx=padx, pady=pady)
    return line


def action_button(
    master,
    text: str,
    command,
    color: str = T.ACCENT,
    hover: str = T.ACCENT_HOVER,
    width: int = 0,
    height: int = 40,
    size: int = 13,
    **kwargs,
) -> ctk.CTkButton:
    """主操作按钮（实心）。"""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        fg_color=color,
        hover_color=hover,
        text_color="#ffffff",
        corner_radius=T.BTN_RADIUS,
        height=height,
        width=width,
        font=T.font(size, "bold"),
        **kwargs,
    )


def ghost_button(
    master,
    text: str,
    command,
    width: int = 0,
    height: int = 32,
    size: int = 12,
    color: str = T.CARD_HOVER,
    hover: str = T.GRAY,
    text_color: str = T.TEXT_DIM,
    **kwargs,
) -> ctk.CTkButton:
    """次要按钮（描边/浅底）。"""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        fg_color=color,
        hover_color=hover,
        text_color=text_color,
        border_width=1,
        border_color=T.BORDER,
        corner_radius=T.BTN_RADIUS,
        height=height,
        width=width,
        font=T.font(size),
        **kwargs,
    )


def field_row(
    master,
    label: str,
    variable,
    placeholder: str = "",
    show: str = None,
    label_width: int = 92,
    **kwargs,
) -> ctk.CTkEntry:
    """一行「标签 + 输入框」。"""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=5)
    ctk.CTkLabel(
        row,
        text=label,
        width=label_width,
        anchor="w",
        font=T.font(12),
        text_color=T.TEXT_DIM,
    ).pack(side="left")
    entry = ctk.CTkEntry(
        row,
        textvariable=variable,
        placeholder_text=placeholder,
        fg_color=T.BG,
        border_color=T.BORDER,
        text_color=T.TEXT,
        placeholder_text_color=T.MUTED,
        corner_radius=8,
        height=34,
        font=T.font(12),
        **kwargs,
    )
    if show:
        try:
            entry.configure(show=show)
        except Exception:
            pass
    entry.pack(side="left", fill="x", expand=True)
    return entry


def path_row(master, label: str, variable, browse_cmd, label_width: int = 92):
    """一行「标签 + 路径输入 + 浏览按钮」。"""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=5)
    ctk.CTkLabel(
        row, text=label, width=label_width, anchor="w",
        font=T.font(12), text_color=T.TEXT_DIM,
    ).pack(side="left")
    ctk.CTkEntry(
        row, textvariable=variable, fg_color=T.BG, border_color=T.BORDER,
        text_color=T.TEXT, corner_radius=8, height=34, font=T.font(12),
    ).pack(side="left", fill="x", expand=True)
    ghost_button(row, "浏览…", browse_cmd, width=64, height=34, size=12).pack(
        side="left", padx=(8, 0)
    )


def switch_row(
    master,
    title: str,
    desc: str,
    variable,
    command=None,
    label_width: int = 0,
) -> ctk.CTkSwitch:
    """一行「标题 + 说明 + 开关」。"""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=7)
    left = ctk.CTkFrame(row, fg_color="transparent")
    left.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(
        left, text=title, font=T.font(13), text_color=T.TEXT, anchor="w"
    ).pack(anchor="w")
    if desc:
        ctk.CTkLabel(
            left, text=desc, font=T.font(11), text_color=T.MUTED, anchor="w",
            justify="left", wraplength=430,
        ).pack(anchor="w", pady=(1, 0))
    sw = ctk.CTkSwitch(
        row,
        text="",
        variable=variable,
        command=command,
        progress_color=T.ACCENT,
        button_color="#ffffff",
        button_hover_color="#e6e6e6",
        width=44,
        height=22,
        switch_width=42,
        switch_height=20,
    )
    sw.pack(side="right", padx=(12, 0))
    return sw


def pill(master, text: str, color: str = T.MUTED, text_color: str = "#ffffff"):
    """小圆角标签（状态徽标）。"""
    return ctk.CTkLabel(
        master,
        text=text,
        fg_color=color,
        text_color=text_color,
        corner_radius=9,
        height=22,
        font=T.font(11, "bold"),
    )


def form_hint(master, text: str, padx: int = 18):
    lbl = ctk.CTkLabel(
        master, text=text, font=T.font(11), text_color=T.MUTED,
        anchor="w", justify="left", wraplength=520,
    )
    lbl.pack(fill="x", padx=padx, pady=(0, 6))
    return lbl
