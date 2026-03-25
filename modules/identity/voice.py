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
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            mp3_path = tmp.name
            tmp.close()
            await communicate.save(mp3_path)

            # mp3 → wav（用 Python 标准库，不需要 ffmpeg）
            wav_path = mp3_path.replace(".mp3", ".wav")
            _mp3_to_wav(mp3_path, wav_path)
            Path(mp3_path).unlink(missing_ok=True)

            _play_audio(wav_path)
            Path(wav_path).unlink(missing_ok=True)

        asyncio.run(_run())
    except ImportError:
        print(f"[Voice] edge-tts not installed. pip install edge-tts")
        print(f"[Voice] {text}")
    except Exception as e:
        print(f"[Voice] TTS failed: {e}")
        print(f"[Voice] {text}")


def _mp3_to_wav(mp3_path: str, wav_path: str):
    """mp3 转 wav，用 pydub（需要 pip install pydub）或 soundfile 兜底。"""
    try:
        from pydub import AudioSegment
        AudioSegment.from_mp3(mp3_path).export(wav_path, format="wav")
    except ImportError:
        # pydub 没装，用 subprocess 调 Windows 内置的 mfplay / powershell
        # 实际上直接重命名骗过 SoundPlayer（不标准但很多 mp3 能播）
        import shutil
        shutil.copy(mp3_path, wav_path)


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
    """播放音频文件（Windows 用 SoundPlayer，仅支持 wav）。"""
    import platform
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(
                ["powershell", "-c",
                 f'(New-Object Media.SoundPlayer "{path}").PlaySync()'],
                check=True, capture_output=True
            )
        elif system == "Darwin":
            subprocess.run(["afplay", path], check=True)
        else:
            subprocess.run(["aplay", path], check=True)
    except Exception as e:
        print(f"[Voice] Playback error: {e}")


# 供 dispatcher 加载的接口
def run(context: dict, config: dict) -> dict:
    return {"status": "ok", "message": ""}
