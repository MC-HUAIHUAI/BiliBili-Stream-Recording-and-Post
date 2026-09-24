"""通用工具函数"""

import os
import re
from datetime import datetime


def chinese_date(dt: datetime = None) -> str:
    """返回如 '2026年9月24日' 的中文日期。"""
    dt = dt or datetime.now()
    return f"{dt.year}年{dt.month}月{dt.day}日"


def build_title(template: str, name: str, dt: datetime = None) -> str:
    """根据模板生成标题，默认模板为 '【{date}录播】{name}的直播回放'。

    {date} 会被替换为直播日期（开始录制时的日期），其余部分均可自定义。
    """
    template = template or "【{date}录播】{name}的直播回放"
    return template.format(date=chinese_date(dt), name=name)


_STAMP_RE = re.compile(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})")


def datetime_from_filename(path: str):
    """从形如 '蕾蕾_20260924_203000.flv' 的文件名解析出录制开始时间，失败返回 None。"""
    m = _STAMP_RE.search(os.path.basename(path))
    if not m:
        return None
    try:
        return datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
            int(m.group(5)),
            int(m.group(6)),
        )
    except ValueError:
        return None


def datetime_from_file(path: str) -> datetime:
    """获取某个录播文件对应的直播日期：优先从文件名解析，否则用文件修改时间，再否则用当前时间。"""
    dt = datetime_from_filename(path)
    if dt:
        return dt
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return datetime.now()


def make_output_filename(name: str, ext: str = ".flv") -> str:
    """生成录制输出文件名，如 '蕾蕾_20260924_203000.flv'。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c not in '\\/:*?"<>|').strip() or "录播"
    return f"{safe_name}_{stamp}{ext}"
