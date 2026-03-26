"""
modules/identity/voice.py — TTS 语音输出模块
支持 edge-tts（免费）/ openai
支持打断：按下热键时停止当前播放
"""
import asyncio
import subprocess
import tempfile
import threading
from pathlib import Path

MANIFEST = {
    "name": "voice",
    "triggers": [],
    "description": "Aria 的语音输出（TTS）",
}

# 全局打断信号
_stop_event = threading.Event()
_play_lock = threading.Lock()


def interrupt():
    """外部调用此函数打断当前 TTS 播放。"""
    _stop_event.set()


def speak(text: str, config: dict):
    """同步入口：让 Aria 说话。"""
    cfg = config.get("identity", {}).get("voice", {})
    if not cfg.get("enabled", True):
        print(f"[Voice] (muted) {text}")
        return

    # 清除上一次的打断信号
    _stop_event.clear()

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
            if not _stop_event.is_set():
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
    播放 mp3，支持打断（_stop_event 被 set 时立即停止）。
    优先级：winmm MCI → simpleaudio → 降级
    """
    import platform
    system = platform.system()

    if system != "Windows":
        try:
            proc = subprocess.Popen(
                ["afplay" if system == "Darwin" else "mpg123", "-q", mp3_path]
            )
            while proc.poll() is None:
                if _stop_event.is_set():
                    proc.terminate()
                    print("[Voice] Interrupted")
                    return
                threading.Event().wait(0.1)
        except Exception as e:
            print(f"[Voice] Playback error: {e}")
        return

    # Windows：winmm MCI（直接播 mp3，支持实时打断）
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        alias = "aria_tts"
        winmm.mciSendStringW(f'open "{mp3_path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f'play {alias}', None, 0, None)  # 非阻塞

        # 轮询播放状态，支持打断
        while True:
            if _stop_event.is_set():
                winmm.mciSendStringW(f'stop {alias}', None, 0, None)
                winmm.mciSendStringW(f'close {alias}', None, 0, None)
                print("[Voice] Interrupted")
                return
            # 查询播放状态
            buf = ctypes.create_unicode_buffer(128)
            winmm.mciSendStringW(f'status {alias} mode', buf, 127, None)
            if buf.value != "playing":
                break
            threading.Event().wait(0.05)  # 50ms 轮询

        winmm.mciSendStringW(f'close {alias}', None, 0, None)
        return
    except Exception as e:
        print(f"[Voice] winmm MCI error: {e}")

    # 降级：simpleaudio
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
            while play_obj.is_playing():
                if _stop_event.is_set():
                    play_obj.stop()
                    print("[Voice] Interrupted")
                    break
                threading.Event().wait(0.05)
            Path(wav_path).unlink(missing_ok=True)
            return
        except Exception as e:
            print(f"[Voice] simpleaudio error: {e}")
            Path(wav_path).unlink(missing_ok=True)

    print(f"[Voice] All playback methods failed, text only")


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
        if not _stop_event.is_set():
            _play_audio(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"[Voice] OpenAI TTS failed: {e}")


# 供 dispatcher 加载的接口
def run(context: dict, config: dict) -> dict:
    return {"status": "ok", "message": ""}
