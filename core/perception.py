"""
core/perception.py — 感知引擎 (Phase 1)
快捷键触发 → 录音 → Whisper 识别 → 截图（按需）
"""
import time
import threading
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional


class Perception:
    def __init__(self, config: dict, on_command: Callable[[dict], None]):
        self.config = config.get("perception", {})
        self.on_command = on_command
        self.running = False
        self._whisper_model = None
        self._recording = False

    # ── Whisper ──────────────────────────────────────────────

    def _load_whisper(self):
        if self._whisper_model is None:
            print("[Perception] Loading Whisper model...")
            from faster_whisper import WhisperModel
            size = self.config.get("whisper_model", "base")
            self._whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
            print(f"[Perception] Whisper '{size}' ready")
        return self._whisper_model

    def transcribe(self, audio_path: str) -> str:
        model = self._load_whisper()
        lang = self.config.get("whisper_language", "zh")
        segments, _ = model.transcribe(
            audio_path,
            language=lang,
            beam_size=5,
            vad_filter=False,
        )
        text = "".join(seg.text for seg in segments).strip()
        print(f"[Perception] Transcribed: {text!r}")
        return text

    # ── 录音 ─────────────────────────────────────────────────

    def record_until_silence(self) -> Optional[str]:
        """
        按下快捷键后开始录，检测到静音自动停。
        返回 wav 文件路径。
        """
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np

            sample_rate = 16000
            silence_sec = self.config.get("silence_timeout", 1.5)
            silence_limit = int(silence_sec * sample_rate / 512)
            min_frames = int(0.3 * sample_rate / 512)  # 至少录 0.3s
            mic_idx = self.config.get("mic_device_index", None)
            if mic_idx == -1:
                mic_idx = None

            print("[Perception] Recording... (speak now)")
            frames = []
            silence_count = 0

            with sd.InputStream(samplerate=sample_rate, channels=1,
                                dtype="float32", blocksize=512,
                                device=mic_idx) as stream:
                while self._recording:
                    data, _ = stream.read(512)
                    frames.append(data.copy())
                    rms = float((data ** 2).mean() ** 0.5)
                    if rms < 0.01:
                        silence_count += 1
                    else:
                        silence_count = 0
                    if len(frames) > min_frames and silence_count > silence_limit:
                        break

            if not frames:
                return None

            import numpy as np
            audio = np.concatenate(frames, axis=0)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(tmp.name, audio, sample_rate)
            print(f"[Perception] Audio saved: {tmp.name}")
            return tmp.name

        except Exception as e:
            print(f"[Perception] Record error: {e}")
            return None

    # ── 截图 ─────────────────────────────────────────────────

    def take_screenshot(self) -> Optional[str]:
        try:
            import mss
            import mss.tools
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = Path(__file__).parent.parent / "data" / "captures"
            out.mkdir(parents=True, exist_ok=True)
            path = out / f"screenshot_{ts}.png"
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[1])
                mss.tools.to_png(img.rgb, img.size, output=str(path))
            print(f"[Perception] Screenshot: {path.name}")
            return str(path)
        except Exception as e:
            print(f"[Perception] Screenshot error: {e}")
            return None

    # ── 快捷键监听 ────────────────────────────────────────────

    def _on_hotkey_press(self):
        """快捷键按下：开始录音。"""
        if self._recording:
            return
        self._recording = True
        # 在新线程里录音，录完后触发处理
        threading.Thread(target=self._handle_recording, daemon=True).start()

    def _on_hotkey_release(self):
        """快捷键松开：停止录音。"""
        self._recording = False

    def _handle_recording(self):
        """录音完成后的处理流程。"""
        audio_path = self.record_until_silence()
        if not audio_path:
            return

        text = self.transcribe(audio_path)
        if not text:
            print("[Perception] Empty transcription, skipping")
            return

        context = {
            "transcript": text,
            "timestamp": datetime.now().isoformat(),
            "audio_path": audio_path,
            "screenshot": None,  # 由 intent 层决定是否需要，再调用 take_screenshot
        }
        self.on_command(context)

    # ── 启动 ─────────────────────────────────────────────────

    def start(self):
        import keyboard
        hotkey = self.config.get("hotkey", "ctrl+`")
        print(f"[Perception] Hotkey: {hotkey!r}  (hold to record, release to send)")

        keyboard.on_press_key(
            hotkey.split("+")[-1],
            lambda e: self._on_hotkey_press() if self._is_hotkey_combo(hotkey) else None,
            suppress=False,
        )
        keyboard.on_release_key(
            hotkey.split("+")[-1],
            lambda e: self._on_hotkey_release(),
            suppress=False,
        )

        self.running = True
        print("[Perception] Listening for hotkey... (Ctrl+C to quit)")
        while self.running:
            time.sleep(0.1)

    def _is_hotkey_combo(self, hotkey: str) -> bool:
        """检查组合键修饰键是否都按下了。"""
        import keyboard
        parts = hotkey.lower().split("+")
        modifiers = parts[:-1]
        for mod in modifiers:
            if not keyboard.is_pressed(mod):
                return False
        return True

    def stop(self):
        self.running = False
        self._recording = False
