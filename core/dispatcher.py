"""
core/dispatcher.py — 调度器 (Phase 1)
根据 intent 路由到对应模块。
"""
import importlib.util
from pathlib import Path


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
            return {"status": "error", "message": f"没有找到模块: {action}"}
        try:
            merged = {**context, **intent.get("params", {})}
            return module.run(merged, self.config)
        except Exception as e:
            print(f"[Dispatcher] Module error ({action}): {e}")
            return {"status": "error", "message": str(e)}

    def list_modules(self) -> list[str]:
        return list(self.modules.keys())
