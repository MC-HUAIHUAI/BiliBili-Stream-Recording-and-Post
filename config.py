"""配置持久化模块"""

import json
import os

APP_NAME = "BiliStreamRecorder"
CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "room_id": "",
    "streamer_name": "蕾蕾",
    "output_dir": "",
    "retention_days": 0,
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
