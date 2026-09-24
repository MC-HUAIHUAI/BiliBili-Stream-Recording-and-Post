"""直播录制模块（基于 streamlink，输出原画 1080p）"""

import threading
import time

from streamlink import Streamlink
from streamlink.exceptions import NoStreamsError, StreamlinkError
from streamlink.stream.hls import HLSStream

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

RECONNECT_DELAY = 5
CHUNK_SIZE = 1024 * 1024


class Recorder:
    """在独立线程中录制的封装，支持断线自动重连与手动停止。"""

    def __init__(self, log=None):
        self._log = log or (lambda msg: None)
        self._stop = threading.Event()
        self._thread = None
        self._on_finish = None
        self.recording = False
        self.bytes_written = 0

    def _build_url(self, room_id: str) -> str:
        room_id = str(room_id).strip()
        if room_id.startswith("http"):
            return room_id
        return f"https://live.bilibili.com/{room_id}"

    def _make_session(self, sessdata: str, buvid3: str) -> Streamlink:
        session = Streamlink()
        session.set_option(
            "http-headers",
            {"User-Agent": USER_AGENT, "Referer": "https://live.bilibili.com/"},
        )
        cookies = {}
        if sessdata:
            cookies["SESSDATA"] = sessdata
        if buvid3:
            cookies["buvid3"] = buvid3
        if cookies:
            session.set_option("http-cookies", cookies)
        return session

    def start(
        self,
        room_id: str,
        output_path: str,
        sessdata: str = "",
        buvid3: str = "",
        on_finish=None,
    ) -> None:
        """启动录制线程。"""
        if self.recording:
            return
        self._stop.clear()
        self._on_finish = on_finish
        self.bytes_written = 0
        self.recording = True
        self._thread = threading.Thread(
            target=self._run,
            args=(room_id, output_path, sessdata, buvid3),
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """请求停止并等待线程结束。"""
        if not self.recording:
            return
        self._log("正在停止录制…")
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self.recording = False

    def _run(self, room_id, output_path, sessdata, buvid3) -> None:
        url = self._build_url(room_id)
        session = self._make_session(sessdata, buvid3)

        tmp_path = output_path

        try:
            streams = session.streams(url)
        except NoStreamsError:
            self._log("[错误] 直播间未开播或不存在，无法录制。")
            self._finish()
            return
        except StreamlinkError as e:
            self._log(f"[错误] 获取直播流失败: {e}")
            self._finish()
            return

        stream = streams.get("best")
        if stream is None:
            self._log("[错误] 未找到可用直播流。")
            self._finish()
            return

        if isinstance(stream, HLSStream):
            self._log("[提示] 使用 HLS 流（原画）。")
        else:
            self._log("[提示] 使用 FLV 流（原画 1080p）。")

        self._log(f"[开始] 录制 -> {tmp_path}")

        while not self._stop.is_set():
            try:
                fd = stream.open()
                with open(tmp_path, "wb") as f:
                    while not self._stop.is_set():
                        data = fd.read(CHUNK_SIZE)
                        if not data:
                            break
                        f.write(data)
                        self.bytes_written += len(data)
                fd.close()
            except Exception as e:
                self._log(f"[警告] 读取直播流出错: {e}")

            if self._stop.is_set():
                break

            self._log(f"[提示] 直播流断开，{RECONNECT_DELAY} 秒后尝试重连…")
            time.sleep(RECONNECT_DELAY)
            try:
                streams = session.streams(url)
                new_stream = streams.get("best")
                if new_stream is None:
                    raise NoStreamsError
                stream = new_stream
            except NoStreamsError:
                self._log("[提示] 直播间已下播，停止录制。")
                break
            except Exception as e:
                self._log(f"[警告] 重连失败: {e}")

        self._log(f"[结束] 录制结束，共写入 {self.bytes_written / 1024 / 1024:.2f} MB。")
        self._finish()

    def _finish(self) -> None:
        self.recording = False
        cb = self._on_finish
        self._on_finish = None
        if cb:
            try:
                cb()
            except Exception:
                pass
