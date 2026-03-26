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

        # initial_prompt 帮助 Whisper 识别游戏/AI 场景专有词
        initial_prompt = self.config.get(
            "whisper_initial_prompt",
            "这是一段中文语音指令，内容可能包含：截图、录屏、分析、提醒、番茄钟、"
            "游戏、ARIA、帮我、录一下、看看这个、归档等词语。"
        )

        segments, _ = model.transcribe(
            audio_path,
            language=lang,
            beam_size=5,
            vad_filter=True,           # 过滤背景噪音
            vad_parameters=dict(
                min_silence_duration_ms=300,   # 300ms 静音视为结束
                speech_pad_ms=100,             # 前后各留 100ms
            ),
            initial_prompt=initial_prompt,
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
            from core.bus import bus
            bus.publish("aria.listening", None)
            bus.publish("aria.state_change", {"state": "listening"})
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
            import cv2
            import numpy as np
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = Path(__file__).parent.parent / "data" / "captures"
            out.mkdir(parents=True, exist_ok=True)
            
            # 获取配置参数
            cfg = self.config.get("screenshot", {})
            target_width = cfg.get("max_width", 1920)
            target_height = cfg.get("max_height", 1080)
            jpeg_quality = cfg.get("jpeg_quality", 80)
            
            with mss.mss() as sct:
                # 获取主显示器信息
                monitor = sct.monitors[1]
                
                # 截取屏幕
                img = sct.grab(monitor)
                
                # 转换为numpy数组进行处理
                img_array = np.array(img)
                
                # 分辨率优化：如果屏幕分辨率过高，进行降采样
                height, width = img_array.shape[:2]
                new_width, new_height = width, height  # 默认使用原始尺寸
                if width > target_width or height > target_height:
                    scale = min(target_width / width, target_height / height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    img_array = cv2.resize(img_array, (new_width, new_height), 
                                         interpolation=cv2.INTER_AREA)
                    print(f"[Perception] Screenshot resized: {width}x{height} -> {new_width}x{new_height}")
                
                # 保存为JPEG格式（更小的文件大小）
                path = out / f"screenshot_{ts}.jpg"
                print(f"[Perception] 准备保存JPEG: {path}")
                
                try:
                    cv2.imwrite(str(path), img_array, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                    print(f"[Perception] JPEG保存成功")
                except Exception as e:
                    print(f"[Perception] JPEG保存失败: {e}")
                    # 尝试降级到PNG
                    path = out / f"screenshot_{ts}.png"
                    cv2.imwrite(str(path), img_array)
                    print(f"[Perception] 降级到PNG保存")
                
                # 计算压缩比
                original_size = len(img.rgb) if hasattr(img, 'rgb') else width * height * 3
                compressed_size = path.stat().st_size
                compression_ratio = original_size / compressed_size if compressed_size > 0 else 1
                
                print(f"[Perception] Screenshot: {path.name} ({new_width}x{new_height}, {compressed_size/1024:.1f}KB, {compression_ratio:.1f}x compression)")
                
                return str(path)
                
        except Exception as e:
            print(f"[Perception] Screenshot error: {e}")
            # 降级到原始实现
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
                print(f"[Perception] Fallback screenshot: {path.name}")
                return str(path)
            except Exception as fallback_e:
                print(f"[Perception] Fallback screenshot error: {fallback_e}")
                return None

    # ── 快捷键监听 ────────────────────────────────────────────

    def _on_hotkey(self):
        """
        按一下热键 → 开始录音（说完静音自动停）
        录音期间再按热键 → 强制停止
        """
        if self._recording:
            # 已在录音，强制停止
            self._recording = False
            return

        # 按下热键时，打断当前 TTS 播放
        try:
            from modules.identity.voice import interrupt
            interrupt()
        except Exception:
            pass

        self._recording = True
        threading.Thread(target=self._handle_recording, daemon=True).start()

    def _handle_recording(self):
        """录音完成后的处理流程。"""
        audio_path = self.record_until_silence()
        self._recording = False
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
            "screenshot": None,
        }
        self.on_command(context)

    # ── 启动 ─────────────────────────────────────────────────

    def start(self):
        import keyboard
        hotkey = self.config.get("hotkey", "ctrl+`")
        print(f"[Perception] Hotkey: {hotkey!r}  (press once to start recording, silence to stop)")

        keyboard.add_hotkey(hotkey, self._on_hotkey, suppress=False)

        self.running = True
        print(f"[Perception] Ready. Press {hotkey} and speak...")
        while self.running:
            time.sleep(0.1)

    def stop(self):
        self.running = False
        self._recording = False
