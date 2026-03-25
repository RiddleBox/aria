"""
main.py — ARIA 启动入口
"""
import sys
import yaml
import signal
from pathlib import Path

# 确保项目根目录在 path 里
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.dispatcher import Dispatcher
from core.intent import parse_intent
from core.perception import Perception
from modules.identity.persona import Persona
from modules.identity.voice import speak


def load_config() -> dict:
    config_path = ROOT / "config" / "settings.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    print("""
    ╔══════════════════════════════╗
    ║   ARIA — AI Runtime Agent   ║
    ║   Say 'aria' to activate    ║
    ╚══════════════════════════════╝
    """)

    config = load_config()
    dispatcher = Dispatcher(config)
    persona = Persona(config)

    print(f"\n[ARIA] Loaded modules: {[m['name'] for m in dispatcher.list_modules()]}")

    def on_command(context: dict):
        """感知层检测到指令后的处理流程。"""
        transcript = context.get("transcript", "")
        print(f"\n[ARIA] Command: {transcript}")

        # 解析意图
        system_prompt = persona.get_system_prompt()
        intent = parse_intent(transcript, config, system_prompt)
        print(f"[ARIA] Intent: {intent}")

        action = intent.get("action", "chat")
        reply = intent.get("reply", "好的")

        if action == "chat":
            # 普通对话，直接回复
            speak(reply, config)
            persona.log_interaction(transcript, "chat", reply)
            return

        # 执行对应模块
        result = dispatcher.dispatch(intent, context)
        print(f"[ARIA] Result: {result}")

        # 语音回复
        final_reply = result.get("message", reply)
        speak(final_reply, config)

        # 记录交互
        persona.log_interaction(transcript, action, final_reply)

    # 启动感知引擎
    perception = Perception(config, on_command)

    # 优雅退出
    def handle_exit(sig, frame):
        print("\n[ARIA] Shutting down...")
        perception.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)

    try:
        perception.start()
    except KeyboardInterrupt:
        handle_exit(None, None)


if __name__ == "__main__":
    main()
