"""直播间信息查询模块（开播检测、房间信息）"""

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

LIVE_STATUS_ONLINE = 1
LIVE_STATUS_ROUND = 2
LIVE_STATUS_OFFLINE = 0


def get_room_info(channel: str, sessdata: str = "") -> dict:
    """根据直播间号/短号/URL 获取房间信息。

    Returns:
        dict: 包含 room_id / uid / live_status / title / uname 等字段，失败返回空 dict。
    """
    channel = _normalize_channel(channel)
    if not channel:
        return {}

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://live.bilibili.com/",
    }
    cookies = {}
    if sessdata:
        cookies["SESSDATA"] = sessdata

    try:
        resp = requests.get(
            "https://api.live.bilibili.com/room/v1/Room/get_info",
            params={"room_id": channel},
            headers=headers,
            cookies=cookies,
            timeout=10,
        )
        data = resp.json()
    except Exception:
        return {}

    if data.get("code") != 0:
        return {}
    return data.get("data") or {}


def is_online(channel: str, sessdata: str = "") -> bool:
    info = get_room_info(channel, sessdata)
    return info.get("live_status") == LIVE_STATUS_ONLINE


def _normalize_channel(channel: str) -> str:
    channel = (channel or "").strip()
    if not channel:
        return ""
    if channel.startswith("http"):
        channel = channel.rstrip("/")
        channel = channel.split("/")[-1].split("?")[0]
    return channel
