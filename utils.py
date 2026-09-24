"""通用工具函数"""

from datetime import datetime


def chinese_date(dt: datetime = None) -> str:
    """返回如 '2026年9月24日' 的中文日期。"""
    dt = dt or datetime.now()
    return f"{dt.year}年{dt.month}月{dt.day}日"


def build_title(template: str, name: str, dt: datetime = None) -> str:
    """根据模板生成标题，默认模板为 '【{date}录播】{name}的直播回放'。"""
    template = template or "【{date}录播】{name}的直播回放"
    return template.format(date=chinese_date(dt), name=name)


def make_output_filename(name: str, ext: str = ".flv") -> str:
    """生成录制输出文件名，如 '蕾蕾_20260924_203000.flv'。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c not in '\\/:*?"<>|').strip() or "录播"
    return f"{safe_name}_{stamp}{ext}"
