"""FLV 时间戳修复

直播断线重连后，后续流的时间戳可能是直播的绝对时间 / 或直接跳变，直接拼接
会造成时间戳不连续（B 站转码报错：视频内部存在时间戳跳变）。

本模块提供：
- FlvNormalizer：录制过程中实时改写时间戳，让多段流拼接后时间轴连续。
- fix_file：修复已经录制好的、含跳变的 FLV 文件。

原理：以“相邻标签时间戳是否发生大跳变”为判断依据（不依赖是否带 FLV 头），
一旦跳变就把后续时间戳整体平移，接在上一个时间戳之后。
"""

import os

JUMP_MS = 5000          # 相邻时间戳跳变阈值（毫秒）
FLV_HEADER_MIN = 9


def _tag_ts(tag) -> int:
    return (tag[7] << 24) | (tag[4] << 16) | (tag[5] << 8) | tag[6]


def _set_tag_ts(tag, ts: int) -> None:
    ts &= 0xFFFFFFFF
    tag[4] = (ts >> 16) & 0xFF
    tag[5] = (ts >> 8) & 0xFF
    tag[6] = ts & 0xFF
    tag[7] = (ts >> 24) & 0xFF


class FlvNormalizer:
    """流式 FLV 归一化：喂入原始流字节，输出时间戳连续的数据。"""

    def __init__(self, write):
        self._write = write
        self._buf = bytearray()
        self._started = False
        self._passthrough = False
        self._offset = 0
        self._prev_ts = None
        self._first = True

    def new_connection(self) -> None:
        # 仅用于标记新连接；实际接续由时间戳跳变检测完成
        pass

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)

        if not self._started:
            if len(self._buf) < FLV_HEADER_MIN:
                return
            if self._buf[0:3] != b"FLV":
                # 不是 FLV，原样透传
                self._passthrough = True
                self._started = True
                self._write(bytes(self._buf))
                self._buf.clear()
                return
            header_size = int.from_bytes(self._buf[5:9], "big") or 9
            total = header_size + 4
            if len(self._buf) < total:
                return
            self._write(bytes(self._buf[:total]))
            del self._buf[:total]
            self._started = True

        if self._passthrough:
            if self._buf:
                self._write(bytes(self._buf))
                self._buf.clear()
            return

        while True:
            if len(self._buf) < 11:
                break
            # 重连段若带新的 FLV 头：跳过，不重复写入
            if self._buf[0:3] == b"FLV":
                if len(self._buf) < FLV_HEADER_MIN:
                    break
                header_size = int.from_bytes(self._buf[5:9], "big") or 9
                total = header_size + 4
                if len(self._buf) < total:
                    break
                del self._buf[:total]
                continue

            data_size = int.from_bytes(self._buf[1:4], "big")
            total = 11 + data_size + 4
            if len(self._buf) < total:
                break
            tag = self._buf[:total]
            del self._buf[:total]
            self._write_tag(tag)

    def _write_tag(self, tag: bytes) -> None:
        ts = _tag_ts(tag)
        if self._first:
            self._offset = -ts          # 第一段归零
            self._first = False
        new_ts = ts + self._offset
        if new_ts < 0:
            new_ts = 0
        if self._prev_ts is not None:
            delta = new_ts - self._prev_ts
            if delta > JUMP_MS or delta < -JUMP_MS:
                # 发生跳变：平移使本标签紧跟上一个时间戳
                self._offset += (self._prev_ts + 1) - new_ts
                new_ts = self._prev_ts + 1
        self._prev_ts = new_ts
        buf = bytearray(tag)
        _set_tag_ts(buf, new_ts)
        self._write(bytes(buf))

    def flush(self) -> None:
        # 结束时不完整的尾块直接丢弃
        self._buf.clear()


def fix_file(path: str, out_path: str = None, log=None) -> str:
    """修复已录制 FLV 的时间戳跳变（原地替换或输出到新文件）。"""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    tmp = out_path or (path + ".fixed.tmp")

    offset = 0
    prev_ts = None
    first = True
    tags = 0
    jumps = 0

    with open(path, "rb") as src, open(tmp, "wb") as dst:
        # 原始 FLV 头
        h = src.read(FLV_HEADER_MIN)
        if len(h) < FLV_HEADER_MIN or h[0:3] != b"FLV":
            raise ValueError("不是有效的 FLV 文件")
        header_size = int.from_bytes(h[5:9], "big") or 9
        extra = src.read(max(0, header_size - 9))
        prev0 = src.read(4)
        dst.write(h + extra + prev0)

        while True:
            hdr = src.read(11)
            if len(hdr) < 11:
                break

            # 重连拼接点若带新的 FLV 头：跳过
            if hdr[0:3] == b"FLV":
                hs = int.from_bytes(hdr[5:9], "big") or 9
                remain = max(0, hs + 4 - 11)
                if remain:
                    src.read(remain)
                continue

            data_size = int.from_bytes(hdr[1:4], "big")
            data = src.read(data_size)
            if len(data) < data_size:
                break
            prevtag = src.read(4)
            if len(prevtag) < 4:
                break

            tag = bytearray(hdr + data)
            ts = _tag_ts(tag)
            if first:
                offset = -ts
                first = False
            new_ts = ts + offset
            if new_ts < 0:
                new_ts = 0
            if prev_ts is not None:
                delta = new_ts - prev_ts
                if delta > JUMP_MS or delta < -JUMP_MS:
                    offset += (prev_ts + 1) - new_ts
                    new_ts = prev_ts + 1
                    jumps += 1
            prev_ts = new_ts
            _set_tag_ts(tag, new_ts)
            dst.write(tag)
            dst.write(prevtag)
            tags += 1

    if out_path is None:
        os.replace(tmp, path)
        return path
    return tmp


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python flvfix.py <输入.flv> [输出.flv]")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    print("正在修复:", src)
    out = fix_file(src, dst)
    print("完成:", out)
