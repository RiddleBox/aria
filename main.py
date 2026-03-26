"""
main.py — ARIA 启动入口 (Phase 1)

流程：
  Ctrl+` 按住 → 录音 → 松开/静音停止
  → Whisper 转文字
  → GPT-4o 解析意图（需要截图吗？做什么？）
  → 如需截图 → mss 截图
  → 路由到对应模块执行
  → edge-tts 语音回应
"""
import sys
import signal
import yaml
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.perception import Perception
from core.intent import parse_intent
from core.dispatcher import Dispatcher
from core.bus import bus
from modules.identity.persona import Persona
from modules.identity.voice import speak


def load_config() -> dict:
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    print("""
╔═══════════════════════════════════╗
║  ARIA — AI Runtime Interface Agent ║
║  Hold Ctrl+` to speak             ║
╚═══════════════════════════════════╝""")

    config = load_config()
    dispatcher = Dispatcher(config)
    persona = Persona(config)

    print(f"[ARIA] Modules: {dispatcher.list_modules()}")

    # ── 核心处理流程 ──────────────────────────────────────────

    def on_command(context: dict):
        transcript = context["transcript"]
        print(f"\n[ARIA] ▶ {transcript!r}")
        bus.publish("aria.transcribed", {"transcript": transcript})

        # 1. 解析意图
        bus.publish("aria.state_change", {"state": "thinking"})
        system_prompt = persona.get_system_prompt()
        intent = parse_intent(transcript, config, system_prompt)
        bus.publish("aria.intent_parsed", {"action": intent.get("action"), "params": intent.get("params", {})})

        # 2. 需要截图？现在截
        if intent.get("needs_screenshot"):
            print("[ARIA] Taking screenshot...")
            screenshot = perception.take_screenshot()
            context["screenshot"] = screenshot
            bus.publish("aria.screenshot_taken", {"path": screenshot})

        # 3. 把 intent 的 reply 和 params 合并进 context
        context["reply"] = intent.get("reply", "")
        context["system_prompt"] = system_prompt  # chat 模块用
        context.update(intent.get("params", {}))

        # 4. 执行模块
        bus.publish("aria.action_start", {"action": intent.get("action"), "context": context})
        result = dispatcher.dispatch(intent, context)
        bus.publish("aria.action_complete", {"action": intent.get("action"), "result": result})
        print(f"[ARIA] Result: status={result.get('status')} msg={result.get('message', '')[:60]}")

        # 5. 语音回应
        bus.publish("aria.state_change", {"state": "speaking"})
        reply_text = result.get("message") or intent.get("reply") or "好的"
        speak(reply_text, config)
        bus.publish("aria.speaking_done", None)
        bus.publish("aria.state_change", {"state": "idle"})

        # 6. 记录交互
        persona.log_interaction(transcript, intent.get("action", "?"), reply_text)

    # ── 启动感知层 ────────────────────────────────────────────

    perception = Perception(config, on_command)

    def handle_exit(sig=None, frame=None):
        print("\n[ARIA] Goodbye.")
        bus.publish("aria.state_change", {"state": "idle"})
        perception.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)

    try:
        perception.start()
    except KeyboardInterrupt:
        handle_exit()


if __name__ == "__main__":
    main()
