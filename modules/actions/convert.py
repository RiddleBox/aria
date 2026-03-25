"""
modules/actions/convert.py — 媒体转换模块
视频 → GIF（ffmpeg）
"""
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

MANIFEST = {
    "name": "convert",
    "triggers": ["转成gif", "转换", "gif", "动图", "转一下"],
    "description": "将视频转换为 GIF 动图（使用 ffmpeg）",
}


def run(context: dict, config: dict) -> dict:
    cfg = config.get("actions", {}).get("convert", {})
    video_path = context.get("video_path")

    if not video_path or not Path(video_path).exists():
        return {"status": "error", "message": "没有找到视频文件"}

    ffmpeg = cfg.get("ffmpeg_path") or shutil.which("ffmpeg")
    if not ffmpeg:
        return {"status": "error", "message": "找不到 ffmpeg，请先安装"}

    fps = cfg.get("gif_fps", 15)
    width = cfg.get("gif_width", 640)
    use_palette = cfg.get("gif_palette", True)

    video_path = Path(video_path)
    gif_path = video_path.with_suffix(".gif")

    try:
        if use_palette:
            # 两步法：先生成调色板，再生成 GIF（画质更好）
            palette_path = video_path.with_suffix(".png")
            scale_filter = f"fps={fps},scale={width}:-1:flags=lanczos"

            # Step 1: 生成调色板
            subprocess.run([
                ffmpeg, "-i", str(video_path),
                "-vf", f"{scale_filter},palettegen",
                "-y", str(palette_path)
            ], check=True, capture_output=True)

            # Step 2: 生成 GIF
            subprocess.run([
                ffmpeg, "-i", str(video_path), "-i", str(palette_path),
                "-filter_complex", f"{scale_filter}[x];[x][1:v]paletteuse",
                "-y", str(gif_path)
            ], check=True, capture_output=True)

            palette_path.unlink(missing_ok=True)
        else:
            # 简单模式
            subprocess.run([
                ffmpeg, "-i", str(video_path),
                "-vf", f"fps={fps},scale={width}:-1:flags=lanczos",
                "-y", str(gif_path)
            ], check=True, capture_output=True)

        size_mb = gif_path.stat().st_size / 1024 / 1024
        print(f"[Convert] GIF saved: {gif_path} ({size_mb:.1f}MB)")
        return {
            "status": "ok",
            "gif": str(gif_path),
            "message": f"GIF 生成完成，{size_mb:.1f}MB",
        }

    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        print(f"[Convert] ffmpeg failed: {err}")
        return {"status": "error", "message": f"转换失败: {err[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
