"""
core/perception.py — 感知引擎
负责：唤醒词检测 → 录音 → Whisper 语音识别 → 截图
"""
import time
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class Perception:
    def __init__(self, config: dict, on_command: Callable[[dict], None]):
        """
        config: settings.yaml 里的 perception 配置
        on_command: 识别到指令后的回调，传入 context dict
        """
        self.config = config.get("perception", {})
        self.on_command = on_command
        self.running = False
        self._model = None

    def _load_whisper(self):
        if self._model is None:
            print("[Perception] Loading Whisper model...")
            from faster_whisper import WhisperModel
            model_size = self.config.get("whisper_model", "base")
            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(f"[Perception] Whisper {model_size} loaded")
        return self._model

    def take_screenshot(self) -> Optional[str]:
        """截取当前屏幕，保存到临时目录，返回文件路径。"""
        try:
            import mss
            import mss.tools
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = Path(__file__).parent.parent / "data" / "captures"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"screenshot_{ts}.png"
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # 主显示器
                img = sct.grab(monitor)
                mss.tools.to_png(img.rgb, img.size, output=str(path))
            print(f"[Perception] Screenshot: {path}")
            return str(path)
        except Exception as e:
            print(f"[Perception] Screenshot failed: {e}")
            return None

    def transcribe(self, audio_path: str) -> str:
        """Whisper 语音转文字。"""
        model = self._load_whisper()
        lang = self.config.get("whisper_language", "zh")
        segments, _ = model.transcribe(
            audio_path,
            language=lang,
            beam_size=1,
            vad_filter=True,
        )
        text = "".join(seg.text for seg in segments).strip()
        print(f"[Perception] Transcribed: {text}")
        return text

    def listen_once(self) -> Optional[str]:
        """
        录制一段语音（检测到静音则停止），返回保存的音频路径。
        """
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np

            sample_rate = 16000
            silence_timeout = self.config.get("silence_timeout", 1.5)
            mic_idx = self.config.get("mic_device_index", None)
            if mic_idx == -1:
                mic_idx = None

            print("[Perception] Listening...")
            frames = []
            silence_frames = 0
            silence_limit = int(silence_timeout * sample_rate / 512)

            with sd.InputStream(samplerate=sample_rate, channels=1,
                                dtype="float32", blocksize=512,
                                device=mic_idx) as stream:
                while True:
                    data, _ = stream.read(512)
                    frames.append(data.copy())
                    rms = np.sqrt(np.mean(data**2))
                    if rms < 0.01:
                        silence_frames += 1
                    else:
                        silence_frames = 0
                    # 至少录 0.5s，然后检测静音
                    if len(frames) > int(0.5 * sample_rate / 512) and silence_frames > silence_limit:
                        break

            audio = np.concatenate(frames, axis=0)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = Path(__file__).parent.parent / "data" / f"audio_{ts}.wav"
            sf.write(str(audio_path), audio, sample_rate)
            return str(audio_path)

        except Exception as e:
            print(f"[Perception] Listen failed: {e}")
            return None

    def start(self):
        """启动感知循环（阻塞）。"""
        self.running = True
        wake_word = self.config.get("wake_word", "aria").lower()
        print(f"[Perception] Started. Wake word: '{wake_word}'")
        print(f"[Perception] Say '{wake_word}' to activate...")

        while self.running:
            audio_path = self.listen_once()
            if not audio_path:
                time.sleep(0.1)
                continue

            text = self.transcribe(audio_path)
            if not text:
                continue

            # 检查是否包含唤醒词
            if wake_word not in text.lower():
                continue

            print(f"[Perception] Wake word detected! Command: {text}")

            # 触发截图
            screenshot = self.take_screenshot()

            # 回调
            context = {
                "transcript": text,
                "screenshot": screenshot,
                "timestamp": datetime.now().isoformat(),
                "audio_path": audio_path,
            }
            self.on_command(context)

    def stop(self):
        self.running = False
