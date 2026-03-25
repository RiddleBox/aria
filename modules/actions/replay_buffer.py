"""
modules/actions/replay_buffer.py — 轻量 Replay Buffer（Phase 2）

原理：后台线程持续用 DXGI（d3dshot）截帧，存入环形队列。
触发时把队列里的帧用 ffmpeg 合成 mp4。

依赖：
  pip install d3dshot comtypes  # DXGI 截帧
  ffmpeg 已在 PATH 中           # 合成视频

用法：
  buf = ReplayBuffer(fps=5, duration_sec=30)
  buf.start()
  # ... 用户触发 ...
  path = buf.save("D:/output/clip_001.mp4")
  buf.stop()
"""

import threading
import time
import subprocess
import tempfile
import shutil
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import Optional


class ReplayBuffer:
    """
    后台截帧 + 环形队列 Replay Buffer。

    fps: 每秒截几帧（5fps 够用，不卡性能）
    duration_sec: 保留最近多少秒（默认 30s）
    """

    def __init__(self, fps: int = 5, duration_sec: int = 30):
        self.fps = fps
        self.duration_sec = duration_sec
        self._max_frames = fps * duration_sec
        self._frames: deque = deque(maxlen=self._max_frames)  # 存 (timestamp, numpy_array)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._capturer = None

    # ── 启动 / 停止 ──────────────────────────────────────────

    def start(self):
        """启动后台截帧线程。"""
        self._capturer = self._init_capturer()
        if self._capturer is None:
            print("[ReplayBuffer] 无可用截帧方案，Replay Buffer 不可用")
            return False

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print(f"[ReplayBuffer] Started: {self.fps}fps, {self.duration_sec}s window")
        return True

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[ReplayBuffer] Stopped")

    # ── 截帧后端（优先 d3dshot，降级到 mss）───────────────────

    def _init_capturer(self):
        # 方案 A：d3dshot（DXGI，游戏兼容性好）
        try:
            import d3dshot
            cap = d3dshot.create(capture_output="numpy")
            print("[ReplayBuffer] Capturer: d3dshot (DXGI)")
            return ("d3dshot", cap)
        except ImportError:
            print("[ReplayBuffer] d3dshot not installed, trying mss...")
        except Exception as e:
            print(f"[ReplayBuffer] d3dshot init failed: {e}, trying mss...")

        # 方案 B：mss（GDI，游戏全屏可能黑屏，但日常场景够用）
        try:
            import mss as mss_lib
            import numpy as np
            print("[ReplayBuffer] Capturer: mss (GDI fallback)")
            return ("mss", None)
        except ImportError:
            print("[ReplayBuffer] mss not installed either")
            return None

    def _capture_loop(self):
        interval = 1.0 / self.fps
        backend, cap = self._capturer

        while self._running:
            t0 = time.time()
            try:
                frame = self._grab_frame(backend, cap)
                if frame is not None:
                    with self._lock:
                        self._frames.append((t0, frame))
            except Exception as e:
                print(f"[ReplayBuffer] Capture error: {e}")

            elapsed = time.time() - t0
            sleep_t = max(0, interval - elapsed)
            time.sleep(sleep_t)

    def _grab_frame(self, backend: str, cap):
        import numpy as np
        if backend == "d3dshot":
            frame = cap.screenshot()  # 返回 PIL Image
            return np.array(frame)
        elif backend == "mss":
            import mss as mss_lib
            with mss_lib.mss() as sct:
                img = sct.grab(sct.monitors[1])
                return np.array(img)
        return None

    # ── 导出视频 ──────────────────────────────────────────────

    def save(self, output_path: str, last_seconds: Optional[int] = None) -> Optional[str]:
        """
        把环形队列里最近 last_seconds 秒的帧合成 mp4。
        output_path: 输出文件路径（.mp4）
        返回实际写入的路径，失败返回 None。
        """
        import cv2
        import numpy as np

        with self._lock:
            frames = list(self._frames)

        if not frames:
            print("[ReplayBuffer] 没有帧，可能刚启动")
            return None

        # 截取最近 N 秒
        if last_seconds:
            cutoff = time.time() - last_seconds
            frames = [(t, f) for t, f in frames if t >= cutoff]

        if not frames:
            print("[ReplayBuffer] 没有足够的帧")
            return None

        print(f"[ReplayBuffer] Saving {len(frames)} frames → {output_path}")

        # 写帧到临时目录，用 ffmpeg 合成
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            h, w = frames[0][1].shape[:2]
            for i, (_, frame) in enumerate(frames):
                # d3dshot 返回 RGBA，转 BGR
                if frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                elif frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(tmp_dir / f"frame_{i:05d}.jpg"), frame,
                            [cv2.IMWRITE_JPEG_QUALITY, 85])

            # ffmpeg 合成
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(self.fps),
                "-i", str(tmp_dir / "frame_%05d.jpg"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "23",          # 质量，18=高质量，28=小文件
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[ReplayBuffer] ffmpeg error: {result.stderr[-300:]}")
                return None

            size_kb = Path(output_path).stat().st_size / 1024
            print(f"[ReplayBuffer] Saved: {output_path} ({size_kb:.0f}KB, {len(frames)} frames)")
            return output_path

        except Exception as e:
            print(f"[ReplayBuffer] Save error: {e}")
            return None
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @property
    def frame_count(self) -> int:
        return len(self._frames)


# ── 单例（供全局复用）────────────────────────────────────────

_buffer: Optional[ReplayBuffer] = None


def get_buffer(config: dict) -> Optional[ReplayBuffer]:
    """获取全局 ReplayBuffer 单例，如果没启动就启动。"""
    global _buffer
    if _buffer is None:
        cfg = config.get("actions", {}).get("replay", {})
        fps = cfg.get("fps", 5)
        duration = cfg.get("duration_sec", 30)
        _buffer = ReplayBuffer(fps=fps, duration_sec=duration)
        ok = _buffer.start()
        if not ok:
            _buffer = None
    return _buffer


# ── 快速测试 ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("测试 ReplayBuffer（录 10 秒后保存）")
    buf = ReplayBuffer(fps=5, duration_sec=30)
    if buf.start():
        print("录制中，10 秒后保存...")
        time.sleep(10)
        out = buf.save("test_replay.mp4", last_seconds=10)
        print(f"结果：{out}")
        buf.stop()
    else:
        print("启动失败，检查 d3dshot / mss 是否安装")
