"""录制 / 上传 / 调度的控制中心（与界面解耦）。"""

import os
from datetime import datetime

import utils
from recorder import Recorder
from scheduler import Scheduler
from uploader import BiliUploader


class Controller:
    """录制 / 上传 / 调度的控制中心。"""

    def __init__(self, log, cfg: dict):
        self.log = log
        self.cfg = cfg
        self.recorder = Recorder(log)
        self.uploader = BiliUploader(log)
        self.scheduler = Scheduler(self, log)
        self.recording = False
        self.recording_source = None
        self.last_recording = None
        self.current_title = None

    @property
    def uploading(self) -> bool:
        return self.uploader.uploading

    def default_output_dir(self) -> str:
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "recordings")

    def _pick_output_dir(self) -> str:
        primary = str(self.cfg.get("output_dir", "")).strip() or self.default_output_dir()
        backup = str(self.cfg.get("backup_dir", "")).strip()
        try:
            min_gb = float(self.cfg.get("min_free_gb", 20) or 0)
        except (TypeError, ValueError):
            min_gb = 20.0

        for d in (primary, backup):
            if d:
                try:
                    os.makedirs(d, exist_ok=True)
                except Exception:
                    pass

        if min_gb <= 0:
            return primary

        free_p = utils.free_space_gb(primary)
        if free_p >= min_gb:
            self.log(f"[空间] 保存位置剩余 {free_p:.1f}G，充足（阈值 {min_gb:.0f}G）。")
            return primary
        self.log(f"[空间] 保存位置剩余 {free_p:.1f}G，低于阈值 {min_gb:.0f}G。")

        if backup:
            free_b = utils.free_space_gb(backup)
            if free_b >= min_gb:
                self.log(f"[空间] 切换到备用保存位置（剩余 {free_b:.1f}G）：{backup}")
                return backup
            self.log(f"[空间] 备用保存位置剩余 {free_b:.1f}G，也不足。")
        else:
            self.log("[空间] 未设置备用保存位置。")

        self.log("[空间] 两个位置均不足，自动删除最早三天的录播…")
        removed = utils.delete_earliest_days(primary, 3, self.log)
        if backup:
            removed += utils.delete_earliest_days(backup, 3, self.log)
        self.log(f"[空间] 已清理 {removed} 个较早录播文件。")

        free_p = utils.free_space_gb(primary)
        if free_p >= min_gb:
            return primary
        if backup:
            free_b = utils.free_space_gb(backup)
            if free_b >= min_gb:
                self.log(f"[空间] 清理后切换到备用保存位置：{backup}")
                return backup
            if free_b > free_p:
                self.log(f"[警告] 空间仍不足，改用剩余较大的备用目录：{backup}")
                return backup
        self.log(f"[警告] 空间仍不足（剩余 {free_p:.1f}G），继续使用主保存位置。")
        return primary

    def start_recording(self, source: str = "manual") -> bool:
        if self.recording:
            return False
        room = str(self.cfg.get("room_id", "")).strip()
        if not room:
            self.log("[错误] 请先在设置中填写直播间号。")
            return False
        out_dir = self._pick_output_dir()
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.log(f"[错误] 无法创建输出目录: {e}")
            return False

        name = str(self.cfg.get("streamer_name", "")).strip() or "主播"
        start_dt = datetime.now()
        title = utils.build_title(self.cfg.get("title_template", ""), name, start_dt)
        filename = utils.make_output_filename(name, ".flv")
        path = os.path.join(out_dir, filename)

        self.log(f"[标题] {title}  （直播日期: {utils.chinese_date(start_dt)}）")
        self.last_recording = path
        self.current_title = title
        self.recording_source = source
        self.recording = True
        self.recorder.start(
            room,
            path,
            self.cfg.get("sessdata", ""),
            self.cfg.get("buvid3", ""),
            on_finish=self._on_recording_finished,
        )
        return True

    def stop_recording(self) -> None:
        if not self.recording:
            return
        self.recorder.stop()

    def _on_recording_finished(self) -> None:
        self.recording = False
        self.recording_source = None
        path = self.last_recording
        if (
            bool(self.cfg.get("auto_upload"))
            and path
            and os.path.exists(path)
            and os.path.getsize(path) > 0
        ):
            self.log("[自动] 录制完成，开始自动上传。")
            self.upload_file(path, title=self.current_title)
        self.cleanup_old_recordings()

    def cleanup_old_recordings(self) -> None:
        days = int(self.cfg.get("retention_days", 0) or 0)
        if days <= 0:
            return
        out_dir = str(self.cfg.get("output_dir", "")).strip() or self.default_output_dir()
        removed = utils.cleanup_old_files(out_dir, days, self.log)
        if removed:
            self.log(f"[清理] 本次共清理 {removed} 个过期录播文件。")

    def upload_file(self, path: str, title: str = None) -> None:
        if self.uploader.uploading:
            self.log("[提示] 已有上传任务进行中。")
            return
        if not path or not os.path.exists(path):
            self.log("[错误] 文件不存在，无法上传。")
            return
        if not title:
            title = self._title_for_file(path)
        self.log(f"[上传] 准备上传: {path}")
        self.uploader.upload(path, title, self.cfg)

    def _title_for_file(self, path: str) -> str:
        name = str(self.cfg.get("streamer_name", "")).strip() or "主播"
        dt = utils.datetime_from_file(path)
        return utils.build_title(self.cfg.get("title_template", ""), name, dt)

    def shutdown(self) -> None:
        self.scheduler.stop()
        if self.recording:
            self.recorder.stop(timeout=5)
