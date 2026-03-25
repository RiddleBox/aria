"""
modules/actions/capture.py — 截图 + 录屏模块
依赖：OBS（Replay Buffer）或纯 Python 录屏备选
"""
from datetime import datetime
from pathlib import Path
import subprocess
import shutil

MANIFEST = {
    "name": "capture",
    "triggers": ["记录", "截图", "录一下", "保存这段", "记下来", "clip"],
    "description": "截取当前屏幕截图，并通过 OBS Replay Buffer 保存前后一段视频",
}


def run(context: dict, config: dict) -> dict:
    cfg = config.get("actions", {}).get("capture", {})
    output_dir = Path(cfg.get("output_dir", "data/captures"))
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {}

    # 1. 截图（perception 层可能已经截了，直接复用）
    screenshot = context.get("screenshot")
    if screenshot and Path(screenshot).exists():
        dest = output_dir / f"capture_{ts}.png"
        shutil.copy(screenshot, dest)
        results["screenshot"] = str(dest)
        print(f"[Capture] Screenshot saved: {dest}")
    else:
        # 自己截一张
        try:
            import mss, mss.tools
            dest = output_dir / f"capture_{ts}.png"
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                mss.tools.to_png(img.rgb, img.size, output=str(dest))
            results["screenshot"] = str(dest)
        except Exception as e:
            print(f"[Capture] Screenshot failed: {e}")

    # 2. OBS Replay Buffer
    video_path = _trigger_obs_replay(cfg, output_dir, ts)
    if video_path:
        results["video"] = video_path

    # 3. 如果用户要求 GIF，触发 convert
    if context.get("make_gif") and video_path:
        from modules.actions import convert as conv_mod
        gif_ctx = {**context, "video_path": video_path}
        conv_result = conv_mod.run(gif_ctx, config)
        if conv_result.get("gif"):
            results["gif"] = conv_result["gif"]

    note = context.get("note", context.get("transcript", ""))
    results["note"] = note
    results["timestamp"] = context.get("timestamp", ts)
    results["status"] = "ok"
    results["message"] = f"已截图{'并录制视频' if results.get('video') else ''}，正在归档"

    # 4. 触发归档
    from modules.actions import archive as arch_mod
    arch_ctx = {**context, **results}
    arch_result = arch_mod.run(arch_ctx, config)
    results["archive"] = arch_result.get("md_path")
    results["message"] = f"记录完成！{'生成了 GIF，' if results.get('gif') else ''}已存入文档"

    return results


def _trigger_obs_replay(cfg: dict, output_dir: Path, ts: str) -> str | None:
    """触发 OBS Replay Buffer 保存，返回视频路径。"""
    obs_host = cfg.get("obs_host", "localhost")
    obs_port = cfg.get("obs_port", 4455)
    obs_password = cfg.get("obs_password", "")

    try:
        import obsws_python as obs
        cl = obs.ReqClient(host=obs_host, port=obs_port, password=obs_password, timeout=5)
        cl.save_replay_buffer()
        print(f"[Capture] OBS Replay Buffer triggered")

        # OBS 会自动保存到它配置的路径，我们等一秒后找最新的视频文件
        import time, glob
        time.sleep(2)

        # 找 OBS 默认录像路径
        obs_output = Path.home() / "Videos"
        candidates = sorted(obs_output.glob("Replay*.mkv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            candidates = sorted(obs_output.glob("Replay*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

        if candidates:
            src = candidates[0]
            dest = output_dir / f"replay_{ts}{src.suffix}"
            shutil.copy(src, dest)
            print(f"[Capture] Video saved: {dest}")
            return str(dest)

    except ImportError:
        print("[Capture] obsws_python not installed, skipping OBS replay")
    except Exception as e:
        print(f"[Capture] OBS replay failed: {e}")

    return None
