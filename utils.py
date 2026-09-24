"""通用工具函数"""

import os
import re
import time
from datetime import datetime

VIDEO_EXTS = {".flv", ".mp4", ".ts", ".mkv", ".mov", ".avi"}


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


def cleanup_old_files(directory: str, retention_days: int, log=None) -> int:
    """删除 directory 下修改时间超过 retention_days 天的视频文件，返回删除数量。

    retention_days <= 0 表示永久保留，不做清理。
    """
    if not retention_days or retention_days <= 0:
        return 0
    if not directory or not os.path.isdir(directory):
        return 0

    cutoff = time.time() - retention_days * 86400
    removed = 0
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if os.path.splitext(name)[1].lower() not in VIDEO_EXTS:
                continue
            path = os.path.join(root, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    removed += 1
                    if log:
                        log(f"[清理] 删除过期录播: {name}")
            except OSError:
                continue
    return removed
