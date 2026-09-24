"""B 站投稿上传模块（基于 bilibili-api-python）"""

import asyncio
import os
import tempfile
import threading

import requests
from bilibili_api import Credential, video_uploader

from live import USER_AGENT

# 生活 -> 日常 分区 ID
TID_LIFE_DAILY = 21


def check_login(cfg: dict):
    """校验 Cookie 是否有效，返回用户名，失败返回 None。"""
    cookies = {
        "SESSDATA": cfg.get("sessdata") or "",
        "bili_jct": cfg.get("bili_jct") or "",
        "buvid3": cfg.get("buvid3") or "",
        "DedeUserID": cfg.get("dedeuserid") or "",
    }
    try:
        r = requests.get(
            "https://api.bilibili.com/x/web-interface/nav",
            cookies=cookies,
            headers={"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com/"},
            timeout=10,
        )
        d = r.json()
        if d.get("code") == 0 and d.get("data", {}).get("isLogin"):
            return d["data"].get("uname") or "已登录"
    except Exception:
        pass
    return None


def make_credential(cfg: dict) -> Credential:
    return Credential(
        sessdata=cfg.get("sessdata") or None,
        bili_jct=cfg.get("bili_jct") or None,
        buvid3=cfg.get("buvid3") or None,
        dedeuserid=cfg.get("dedeuserid") or None,
        ac_time_value=cfg.get("ac_time_value") or None,
    )


def generate_cover(title: str, path: str) -> str:
    """生成一张 1920x1080 的默认封面（深色底 + 标题文字）。"""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1920, 1080), (30, 30, 40))
    draw = ImageDraw.Draw(img)

    font = None
    for fp in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ):
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 72)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), title, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((1920 - w) // 2, (1080 - h) // 2), title, fill=(255, 255, 255), font=font)

    img.save(path, format="PNG")
    return path


class BiliUploader:
    """在独立线程中执行异步上传任务。"""

    def __init__(self, log=None):
        self._log = log or (lambda msg: None)
        self._thread = None
        self._loop = None
        self._uploader = None
        self.uploading = False
        self.result = None

    def upload(self, file_path: str, title: str, cfg: dict) -> None:
        if self.uploading:
            self._log("[提示] 已有上传任务进行中。")
            return
        self.uploading = True
        self.result = None
        self._thread = threading.Thread(
            target=self._run, args=(file_path, title, cfg), daemon=True
        )
        self._thread.start()

    def cancel(self) -> None:
        if self.uploading and self._loop and self._uploader:
            try:
                asyncio.run_coroutine_threadsafe(self._uploader.abort(), self._loop)
            except Exception:
                pass

    def _run(self, file_path, title, cfg) -> None:
        self._loop = asyncio.new_event_loop()
        try:
            result = self._loop.run_until_complete(self._do_upload(file_path, title, cfg))
            self.result = result
        except Exception as e:
            self._log(f"[错误] 上传失败: {e}")
            self.result = None
        finally:
            try:
                self._loop.close()
            except Exception:
                pass
            self.uploading = False

    async def _do_upload(self, file_path: str, title: str, cfg: dict) -> dict:
        credential = make_credential(cfg)
        if not credential.sessdata or not credential.bili_jct:
            raise ValueError("缺少 Cookie（SESSDATA / bili_jct），无法上传。")

        tags = [t.strip() for t in str(cfg.get("tags", "")).split(",") if t.strip()]
        if not tags:
            tags = ["录播"]
        tags = tags[:10]

        desc = str(cfg.get("desc", "")).strip() or "B站直播录播回放"

        cover_path = os.path.join(
            tempfile.gettempdir(), "bili_cover_" + str(threading.get_ident()) + ".png"
        )
        generate_cover(title, cover_path)

        page = video_uploader.VideoUploaderPage(
            path=file_path, title=title, description=desc
        )
        meta = video_uploader.VideoMeta(
            tid=TID_LIFE_DAILY,
            title=title,
            desc=desc,
            cover=cover_path,
            tags=tags,
            original=True,
        )

        uploader = video_uploader.VideoUploader(
            pages=[page], meta=meta, credential=credential
        )
        self._uploader = uploader

        uploader.add_event_listener("PREUPLOAD", self._on_preupload)
        uploader.add_event_listener("AFTER_CHUNK", self._on_chunk)
        uploader.add_event_listener("PRE_PAGE_SUBMIT", self._on_pre_page_submit)
        uploader.add_event_listener("PRE_SUBMIT", self._on_pre_submit)

        self._log(f"[上传] 开始上传: {os.path.basename(file_path)}")
        self._log(f"[上传] 标题: {title}")
        self._log(f"[上传] 标签: {', '.join(tags)}")

        result = await uploader.start()

        bvid = ""
        if isinstance(result, dict):
            bvid = result.get("bvid") or ""
            if not bvid and isinstance(result.get("data"), dict):
                bvid = result["data"].get("bvid") or ""
        self._log(f"[上传] 投稿成功！BV号: {bvid or result}")
        return result

    def _on_preupload(self, data) -> None:
        self._log("[上传] 获取上传信息…")

    def _on_chunk(self, data) -> None:
        num = int(data.get("chunk_number", 0)) + 1
        total = int(data.get("total_chunk_count", 0))
        if total:
            pct = num * 100.0 / total
            self._log(f"[上传] 进度 {pct:.1f}% ({num}/{total})")

    def _on_pre_page_submit(self, data) -> None:
        self._log("[上传] 分块上传完成，正在合并…")

    def _on_pre_submit(self, data) -> None:
        self._log("[上传] 正在提交稿件…")
