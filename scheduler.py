"""定时 / 自动检测调度模块"""

import threading
import time
from datetime import datetime

import live


class Scheduler:
    """后台调度线程：支持定时录制与开播自动检测。"""

    def __init__(self, controller, log=None):
        self.controller = controller
        self._log = log or (lambda msg: None)
        self._stop = threading.Event()
        self._thread = None
        self._last_auto_check = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                self._log(f"[调度] 出错: {e}")
            self._stop.wait(1)

    def _tick(self) -> None:
        cfg = self.controller.cfg
        now = datetime.now()
        now_hm = now.strftime("%H:%M")

        if cfg.get("schedule_enabled"):
            start = cfg.get("schedule_start", "20:00")
            end = cfg.get("schedule_end", "23:00")
            if self._within(now_hm, start, end):
                if not self.controller.recording:
                    self._log("[定时] 到达设定时间，开始录制。")
                    self.controller.start_recording(source="schedule")
            else:
                if (
                    self.controller.recording
                    and self.controller.recording_source == "schedule"
                ):
                    self._log("[定时] 到达结束时间，停止录制。")
                    self.controller.stop_recording()

        if cfg.get("autodetect_enabled"):
            interval = max(1, int(cfg.get("autodetect_interval", 5) or 5))
            if time.time() - self._last_auto_check >= interval * 60:
                self._last_auto_check = time.time()
                room = str(cfg.get("room_id", "")).strip()
                if not room:
                    self._log("[自动检测] 未填写直播间号，跳过本次检测。")
                else:
                    self._log(f"[自动检测] 正在检测直播间 {room} 是否开播…")
                    info = live.get_room_info(room, cfg.get("sessdata") or "")
                    if not info:
                        self._log("[自动检测] 检测失败（网络错误或直播间不存在）。")
                    else:
                        status = info.get("live_status")
                        title = info.get("title", "")
                        extra = f"（标题: {title}）" if title else ""
                        if status == live.LIVE_STATUS_ONLINE:
                            self._log(f"[自动检测] 开播中{extra}")
                            if not self.controller.recording:
                                self._log("[自动检测] 检测到开播，开始录制。")
                                self.controller.start_recording(source="autodetect")
                        else:
                            self._log(f"[自动检测] 未开播（状态码 {status}）。")
                            if (
                                self.controller.recording
                                and self.controller.recording_source == "autodetect"
                            ):
                                self._log("[自动检测] 检测到下播，停止录制。")
                                self.controller.stop_recording()

    @staticmethod
    def _within(hm: str, start: str, end: str) -> bool:
        if start <= end:
            return start <= hm < end
        return hm >= start or hm < end
