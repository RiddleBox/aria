"""
modules/identity/voice.py — TTS 语音输出模块
支持 edge-tts（免费）/ openai / elevenlabs
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
    """使用 edge-tts（免费，微软云，需联网）。"""
    try:
        import edge_tts
        voice = cfg.get("edge_voice", "zh-CN-XiaoxiaoNeural")
        rate = cfg.get("rate", "+0%")
        volume = cfg.get("volume", "+0%")

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            await communicate.save(tmp_path)
            _play_audio(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)

        asyncio.run(_run())
    except ImportError:
        print(f"[Voice] edge-tts not installed. pip install edge-tts")
        print(f"[Voice] {text}")
    except Exception as e:
        print(f"[Voice] TTS failed: {e}")
        print(f"[Voice] {text}")


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
        _play_audio(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"[Voice] OpenAI TTS failed: {e}")


def _play_audio(path: str):
    """播放音频文件（Windows 优先用 PowerShell）。"""
    import platform
    import subprocess
    system = platform.system()
    try:
        if system == "Windows":
            # PowerShell Media.SoundPlayer 只支持 wav，mp3 用 wmplayer
            if path.endswith(".wav"):
                subprocess.run(
                    ["powershell", "-c", f'(New-Object Media.SoundPlayer "{path}").PlaySync()'],
                    check=True, capture_output=True
                )
            else:
                # mp3 用 Windows Media Player CLI
                subprocess.run(
                    ["powershell", "-c",
                     f'$player = New-Object System.Windows.Media.MediaPlayer; '
                     f'Add-Type -AssemblyName PresentationCore; '
                     f'$player.Open([System.Uri]"{path}"); '
                     f'$player.Play(); Start-Sleep -Seconds 10; $player.Stop()'],
                    check=True, capture_output=True, timeout=30
                )
        elif system == "Darwin":
            subprocess.run(["afplay", path], check=True)
        else:
            subprocess.run(["aplay", path], check=True)
    except Exception as e:
        print(f"[Voice] Playback error: {e}")
        # 最后兜底：playsound
        try:
            import playsound
            playsound.playsound(path)
        except Exception:
            print(f"[Voice] Could not play audio: {path}")


# 供 dispatcher 加载的接口
def run(context: dict, config: dict) -> dict:
    return {"status": "ok", "message": ""}
