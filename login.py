"""B 站扫码登录（封装 bilibili_api.login_v2）。

设计要点：
- 扫码流程是异步的，这里把 asyncio 事件循环放进独立线程，
  通过 queue 把「二维码图片 / 状态变化 / 登录成功 / 出错」推给界面线程。
- 登录成功后除了拿到 sessdata / bili_jct / DedeUserID / ac_time_value，
  还会额外补取 buvid3（扫码接口不返回，录制和投稿都需要它）。
"""

import asyncio
import io
import queue
import threading

import httpx
from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginChannel, QrCodeLoginEvents
from PIL import Image

# 事件类型
EV_QR = "qr"
EV_STATE = "state"
EV_DONE = "done"
EV_ERROR = "error"

STATE_TEXT = {
    QrCodeLoginEvents.SCAN: "等待扫码",
    QrCodeLoginEvents.CONF: "已扫码，请在手机上确认登录",
    QrCodeLoginEvents.TIMEOUT: "二维码已过期",
    QrCodeLoginEvents.DONE: "登录成功",
}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

SPI_URL = "https://api.bilibili.com/x/frontend/finger/spi"


async def fetch_buvid3(sessdata: str = "") -> str:
    """取一个 buvid3。

    优先用 bilibili_api 自带的 get_buvid()，失败再退回 finger/spi 接口。
    扫码登录接口本身不返回 buvid3，但录制与投稿都需要它。
    """
    try:
        from bilibili_api.utils.network import get_buvid

        buvid3, _buvid4 = await get_buvid()
        if buvid3:
            return str(buvid3)
    except Exception:
        pass

    try:
        cookies = {"SESSDATA": sessdata} if sessdata else None
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
        ) as client:
            resp = await client.get(SPI_URL, cookies=cookies)
            data = resp.json().get("data") or {}
            return str(data.get("b_3") or "")
    except Exception:
        return ""


class QrLoginSession:
    """一次扫码登录会话。start() 后通过 queue 读取事件。"""

    def __init__(self, log=None, platform=QrCodeLoginChannel.WEB, poll_interval: float = 2.0):
        self._log = log or (lambda msg: None)
        self.queue: "queue.Queue[dict]" = queue.Queue()
        self.poll_interval = poll_interval
        self._platform = platform
        self._stop = threading.Event()
        self._thread = None

    # ---------- 生命周期 ----------
    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self._stop.clear()
        if self.alive:
            return
        self._thread = threading.Thread(target=self._run, name="qr-login", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ---------- 内部 ----------
    def _emit(self, type_: str, **kw) -> None:
        self.queue.put({"type": type_, **kw})

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._main())
        except Exception as e:  # 网络异常 / 接口变动
            if not self._stop.is_set():
                msg = str(e) or e.__class__.__name__
                self._emit(EV_ERROR, msg=msg)
                self._log(f"[登录] 扫码登录失败: {msg}")
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _main(self) -> None:
        qr = QrCodeLogin(self._platform)
        await qr.generate_qrcode()
        try:
            raw = qr.get_qrcode_picture().content
            image = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception as e:
            raise RuntimeError(f"二维码图片解析失败: {e}")
        self._emit(EV_QR, image=image)
        self._log("[登录] 二维码已生成，请用 B站 手机客户端扫码。")

        last_state = None
        fails = 0
        while not self._stop.is_set():
            try:
                state = await qr.check_state()
                fails = 0
            except Exception as e:
                fails += 1
                if fails >= 3:
                    raise RuntimeError(f"轮询登录状态失败: {e}")
                await asyncio.sleep(self.poll_interval)
                continue

            if state != last_state:
                last_state = state
                self._emit(EV_STATE, state=state)
                self._log(f"[登录] 状态：{STATE_TEXT.get(state, str(state))}")

            if state == QrCodeLoginEvents.DONE:
                cred = qr.get_credential()
                data = {
                    "sessdata": cred.sessdata or "",
                    "bili_jct": cred.bili_jct or "",
                    "dedeuserid": cred.dedeuserid or "",
                    "ac_time_value": cred.ac_time_value or "",
                    "buvid3": "",
                }
                data["buvid3"] = await fetch_buvid3(data["sessdata"])
                if not data["buvid3"]:
                    self._log("[登录] 警告：未能取到 buvid3，投稿可能受影响。")
                self._emit(EV_DONE, cred=data)
                return

            if state == QrCodeLoginEvents.TIMEOUT:
                return

            await asyncio.sleep(self.poll_interval)
