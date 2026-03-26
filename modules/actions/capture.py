"""
modules/actions/capture.py — 截图 + 录屏模块
支持：截图 / ReplayBuffer 保存过去N秒 / 录制未来N秒
"""
from datetime import datetime
from pathlib import Path
import subprocess
import shutil
import time
import threading

MANIFEST = {
    "name": "capture",
    "triggers": ["录", "录制", "截图", "录一下", "保存这段", "记下来", "clip", "录屏", "录视频"],
    "description": "截取屏幕截图，或录制指定时长的屏幕视频",
}


def run(context: dict, config: dict) -> dict:
    cfg = config.get("actions", {}).get("capture", {})
    output_dir = Path(cfg.get("output_dir", "data/captures"))
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    duration = int(context.get("duration", 10))  # 从 intent params 读时长，默认10秒
    print(f"[Capture] Will record {duration}s")
    results = {}
    screenshot = context.get("screenshot")
    if not screenshot:
        try:
            import mss, mss.tools
            dest = output_dir / f"capture_{ts}.png"
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                mss.tools.to_png(img.rgb, img.size, output=str(dest))
            screenshot = str(dest)
        except Exception as e:
            print(f"[Capture] Screenshot failed: {e}")

    if screenshot:
        results["screenshot"] = screenshot

    # 2. 录制视频（用 mss 逐帧截图 + ffmpeg 合成）
    video_path = _record_screen(output_dir, ts, duration)
    if video_path:
        results["video"] = video_path
        results["status"] = "ok"
        results["message"] = f"录好了，{duration}秒视频已保存到 {Path(video_path).name}"
    else:
        results["status"] = "ok"
        results["message"] = f"截图已保存，视频录制失败（ffmpeg 没找到，检查一下 PATH）"

    results["note"] = context.get("note", context.get("transcript", ""))
    results["timestamp"] = ts

    # 3. 归档截图到 vault
    if screenshot:
        try:
            from modules.actions import archive as arch_mod
            arch_ctx = {**context, **results}
            arch_result = arch_mod.run(arch_ctx, config)
            results["archive"] = arch_result.get("md_path")
        except Exception as e:
            print(f"[Capture] Archive failed: {e}")

    return results


def _record_screen(output_dir: Path, ts: str, duration: int) -> str | None:
    """用 mss 逐帧截图，ffmpeg 合成 mp4。"""
    import numpy as np

    fps = 10  # 录屏帧率，10fps 够看
    # 用项目内的 tmp 目录，避免系统 temp 的短路径问题
    tmp_dir = output_dir / f"_tmp_{ts}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"capture_{ts}.mp4"

    print(f"[Capture] Recording {duration}s at {fps}fps...")

    try:
        import mss
        import cv2

        frame_count = 0
        interval = 1.0 / fps
        end_time = time.time() + duration

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            while time.time() < end_time:
                t0 = time.time()
                img = sct.grab(monitor)
                frame = np.array(img)
                # BGRA → BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                # 降分辨率（保持比例，宽度最大 1280）
                h, w = frame.shape[:2]
                if w > 1280:
                    scale = 1280 / w
                    frame = cv2.resize(frame, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(tmp_dir / f"frame_{frame_count:05d}.jpg"), frame,
                            [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_count += 1
                elapsed = time.time() - t0
                time.sleep(max(0, interval - elapsed))

        print(f"[Capture] Captured {frame_count} frames -> {tmp_dir}")

        # ffmpeg 合成
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        print(f"[Capture] ffmpeg: {ffmpeg_path}")
        result = subprocess.run([
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-i", str(tmp_dir / "frame_%05d.jpg"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "26",
            str(output_path)
        ], capture_output=True, timeout=60)

        if result.returncode != 0:
            err = result.stderr.decode(errors="ignore")
            print(f"[Capture] ffmpeg error: {err[-500:]}")
            return None

        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"[Capture] Video saved: {output_path} ({size_mb:.1f}MB)")
        return str(output_path)

    except ImportError as e:
        print(f"[Capture] Missing dependency: {e}")
        return None
    except Exception as e:
        print(f"[Capture] Record error: {e}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
