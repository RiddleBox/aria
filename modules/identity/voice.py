"""
modules/identity/voice.py — TTS 语音输出模块
支持 edge-tts（免费）/ openai
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path

MANIFEST = {
    "name": "voice",
    "triggers": [],
    "description": "Aria 的语音输出（TTS）",
}


def speak(text: str, config: dict):
    """同步入口：让 Aria 说话。"""
    cfg = config.get("identity", {}).get("voice", {})
    if not cfg.get("enabled", True):
        print(f"[Voice] (muted) {text}")
        return

    engine = cfg.get("engine", "edge-tts")
    if engine == "edge-tts":
        _speak_edge(text, cfg)
    elif engine == "openai":
        _speak_openai(text, cfg, config)
    else:
        print(f"[Voice] {text}")


def _speak_edge(text: str, cfg: dict):
    """使用 edge-tts 生成 mp3，用 Windows Media Player 播放。"""
    try:
        import edge_tts
        voice = cfg.get("edge_voice", "zh-CN-XiaoxiaoNeural")
        rate = cfg.get("rate", "+0%")
        volume = cfg.get("volume", "+0%")

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            mp3_path = tmp.name
            tmp.close()
            await communicate.save(mp3_path)
            _play_mp3(mp3_path)
            Path(mp3_path).unlink(missing_ok=True)

        asyncio.run(_run())
    except ImportError:
        print(f"[Voice] edge-tts not installed. pip install edge-tts")
        print(f"[Voice] {text}")
    except Exception as e:
        print(f"[Voice] TTS failed: {e}")
        print(f"[Voice] {text}")


def _play_mp3(path: str):
    """用 Windows Media Player COM 对象播放 mp3（同步等待播完）。"""
    import platform
    system = platform.system()
    try:
        if system == "Windows":
            # WMP COM 对象，播完自动退出
            ps_script = (
                f'$wmp = New-Object -ComObject WMPlayer.OCX; '
                f'$wmp.settings.volume = 100; '
                f'$wmp.URL = "{path}"; '
                f'$wmp.controls.play(); '
                f'Start-Sleep -Milliseconds 500; '
                f'while ($wmp.playState -ne 1) {{ Start-Sleep -Milliseconds 200 }}; '
                f'$wmp.close()'
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-c", ps_script],
                capture_output=True, timeout=30
            )
            if result.returncode != 0:
                err = result.stderr.decode(errors="ignore")
                print(f"[Voice] WMP error: {err[:100]}")
        elif system == "Darwin":
            subprocess.run(["afplay", path], check=True)
        else:
            subprocess.run(["mpg123", "-q", path], check=True)
    except Exception as e:
        print(f"[Voice] Playback error: {e}")


def _speak_openai(text: str, cfg: dict, full_config: dict):
    """使用 OpenAI TTS。"""
    try:
        import os
        from openai import OpenAI
        api_key = full_config.get("intent", {}).get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        client = OpenAI(api_key=api_key)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        resp = client.audio.speech.create(model="tts-1", voice="nova", input=text)
        resp.stream_to_file(tmp_path)
        _play_mp3(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"[Voice] OpenAI TTS failed: {e}")


# 供 dispatcher 加载的接口
def run(context: dict, config: dict) -> dict:
    return {"status": "ok", "message": ""}
