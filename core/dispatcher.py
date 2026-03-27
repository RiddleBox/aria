"""
core/dispatcher.py — 调度器 (Phase 1)
根据 intent 路由到对应模块。
找不到模块时调用 skill_finder，推荐可能满足需求的外部资源。
"""
import importlib.util
from pathlib import Path
from datetime import datetime
from core.bus import bus
from core.skill_finder import find as skill_find


class Dispatcher:
    def __init__(self, config: dict):
        self.config = config
        self.modules: dict[str, object] = {}
        self._load_modules()

    def _load_modules(self):
        modules_dir = Path(__file__).parent.parent / "modules"
        for py_file in modules_dir.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "MANIFEST"):
                    name = mod.MANIFEST["name"]
                    self.modules[name] = mod
                    print(f"[Dispatcher] Module loaded: {name}")
            except Exception as e:
                print(f"[Dispatcher] Failed to load {py_file.name}: {e}")

    def dispatch(self, intent: dict, context: dict) -> dict:
        action = intent.get("action", "chat")
        module = self.modules.get(action)
        if not module:
            # 找不到模块 → 调用 skill_finder 推荐外部资源
            transcript = context.get("transcript", "")
            finder_result = skill_find(action, transcript)
            bus.publish("aria.skill_not_found", {
                "action": action,
                "suggestions": finder_result.get("suggestions", []),
            })
            return {
                "status": "skill_not_found",
                "action": action,
                "message": finder_result["message"],
                "suggestions": finder_result.get("suggestions", []),
            }
        try:
            merged = {**context, **intent.get("params", {})}
            result = module.run(merged, self.config)
        except Exception as e:
            print(f"[Dispatcher] Module error ({action}): {e}")
            result = {"status": "error", "message": str(e)}

        # 广播事件，供 Godot 等外部监听方订阅
        bus.publish("aria.action_complete", {
            "event": "aria.action_complete",
            "action": action,
            "reply": result.get("message", ""),
            "timestamp": datetime.now().isoformat(),
            "status": result.get("status", "ok"),
            "data": result,
        })
        return result

    def list_modules(self) -> list[str]:
        return list(self.modules.keys())
