"""
modules/identity/persona.py — 性格与记忆模块
管理 Aria 的人格、对话风格、短期记忆
"""
import json
from pathlib import Path
from datetime import datetime

MANIFEST = {
    "name": "persona",
    "triggers": [],  # identity 模块不直接响应指令，由 core 加载
    "description": "Aria 的性格、对话风格、记忆管理",
}


class Persona:
    def __init__(self, config: dict):
        cfg = config.get("identity", {}).get("persona", {})
        self.name = cfg.get("name", "Aria")
        self.personality = cfg.get("personality", "你是一个简洁友好的助手。")
        self.memory_file = Path(cfg.get("memory_file", "data/aria_memory.json"))
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self._memory = self._load_memory()

    def _load_memory(self) -> dict:
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text(encoding="utf-8"))
            except:
                pass
        return {"interactions": [], "facts": {}}

    def save_memory(self):
        self.memory_file.write_text(
            json.dumps(self._memory, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_system_prompt(self) -> str:
        """返回注入到 LLM 的 system prompt。"""
        facts = self._memory.get("facts", {})
        facts_str = ""
        if facts:
            facts_str = "\n已知用户信息：\n" + "\n".join(f"- {k}: {v}" for k, v in facts.items())

        return f"{self.personality}{facts_str}"

    def remember_fact(self, key: str, value: str):
        """记住关于用户的一个事实。"""
        self._memory["facts"][key] = value
        self.save_memory()

    def log_interaction(self, transcript: str, action: str, result: str):
        """记录一次交互（只保留最近100条）。"""
        self._memory["interactions"].append({
            "time": datetime.now().isoformat(),
            "transcript": transcript,
            "action": action,
            "result": result,
        })
        self._memory["interactions"] = self._memory["interactions"][-100:]
        self.save_memory()


# 运行接口（供 dispatcher 加载）
def run(context: dict, config: dict) -> dict:
    # persona 不直接响应指令，返回空
    return {"status": "ok", "message": ""}
