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
    """使用 edge-tts 生成音频并播放。"""
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
            _play_audio(mp3_path)
            Path(mp3_path).unlink(missing_ok=True)

        asyncio.run(_run())
    except ImportError:
        print(f"[Voice] edge-tts not installed. pip install edge-tts")
        print(f"[Voice] {text}")
    except Exception as e:
        print(f"[Voice] TTS failed: {e}")
        print(f"[Voice] {text}")


def _play_audio(mp3_path: str):
    """
    播放 mp3 文件，按优先级尝试多种方案：
    1. winmm MCI 命令（Windows 原生，无超时风险）
    2. simpleaudio（mp3→wav 转换后播放）
    3. 静默降级（只打印文字）
    """
    import platform
    system = platform.system()

    if system != "Windows":
        # macOS / Linux
        try:
            subprocess.run(["afplay" if system == "Darwin" else "mpg123", "-q", mp3_path],
                           check=True, timeout=60)
        except Exception as e:
            print(f"[Voice] Playback error: {e}")
        return

    # Windows：优先用 winmm MCI（直接播 mp3，无依赖，无超时问题）
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        alias = "aria_tts"
        winmm.mciSendStringW(f'open "{mp3_path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
        winmm.mciSendStringW(f'close {alias}', None, 0, None)
        return
    except Exception as e:
        print(f"[Voice] winmm MCI error: {e}")

    # 降级：simpleaudio（需要先转 wav）
    wav_path = mp3_path.replace(".mp3", ".wav")
    converted = False
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "22050", "-ac", "1", wav_path],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            converted = True
    except Exception:
        pass

    if converted:
        try:
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(wav_path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            Path(wav_path).unlink(missing_ok=True)
            return
        except Exception as e:
            print(f"[Voice] simpleaudio error: {e}")
            Path(wav_path).unlink(missing_ok=True)

    print(f"[Voice] All playback methods failed, text only")


def _mp3_to_wav(mp3_path: str, wav_path: str):
    """
    用 pydub 或 mutagen 把 mp3 转 wav（ffmpeg 不可用时的纯 Python 方案）。
    edge-tts 实际上支持直接输出 wav，但接口是 mp3，所以这里做转换兜底。
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(mp3_path)
        audio.export(wav_path, format="wav")
    except ImportError:
        raise RuntimeError("pydub not available")


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


# 供 dispatcher 加载的接口
def run(context: dict, config: dict) -> dict:
    return {"status": "ok", "message": ""}
