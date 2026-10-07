"""配置持久化模块"""

import json
import os
import sys

APP_NAME = "BiliStreamRecorder"
CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def get_log_dir() -> str:
    """返回日志目录：优先软件安装目录下的 log，不可写时回退到 %APPDATA%。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(base, "log")
    try:
        os.makedirs(target, exist_ok=True)
        probe = os.path.join(target, ".write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("")
        os.remove(probe)
        return target
    except OSError:
        fallback = os.path.join(CONFIG_DIR, "log")
        os.makedirs(fallback, exist_ok=True)
        return fallback

DEFAULT_CONFIG = {
    "room_id": "",
    "streamer_name": "",
    "output_dir": "",
    "backup_dir": "",
    "retention_days": 0,
    "min_free_gb": 20,
    "cover_mode": "text",
    "cover_image": "",
    "auto_upload": True,
    "sessdata": "",
    "bili_jct": "",
    "buvid3": "",
    "dedeuserid": "",
    "ac_time_value": "",
    "tags": "录播,直播",
    "desc": "B站直播录播回放",
    "title_template": "【{date}录播】{name}的直播回放",
    "schedule_enabled": False,
    "schedule_start": "20:00",
    "schedule_end": "23:00",
    "autodetect_enabled": False,
    "autodetect_interval": 5,
    "autostart": False,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
