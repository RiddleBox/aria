"""
core/dispatcher.py — 模块调度器
负责：加载所有模块、根据 intent 路由到对应模块并执行。
"""
import importlib
import importlib.util
import os
from pathlib import Path
from typing import Optional


class Dispatcher:
    def __init__(self, config: dict):
        self.config = config
        self.modules: dict[str, object] = {}  # name -> module
        self._load_modules()

    def _load_modules(self):
        """扫描 modules/ 目录，自动加载所有启用的模块。"""
        modules_dir = Path(__file__).parent.parent / "modules"
        for category in ["actions", "identity"]:
            cat_dir = modules_dir / category
            if not cat_dir.exists():
                continue
            for py_file in cat_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = py_file.stem
                # 检查配置里是否启用
                cat_config = self.config.get(category if category != "actions" else "actions", {})
                module_config = cat_config.get(module_name, {})
                if not module_config.get("enabled", True):
                    print(f"[Dispatcher] Skipping disabled module: {module_name}")
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "MANIFEST"):
                        self.modules[module_name] = mod
                        print(f"[Dispatcher] Loaded module: {module_name} — {mod.MANIFEST.get('description', '')}")
                except Exception as e:
                    print(f"[Dispatcher] Failed to load {module_name}: {e}")

    def dispatch(self, intent: dict, context: dict) -> dict:
        """
        根据意图路由到模块并执行。
        intent: {"action": "capture", "params": {...}}
        context: {"transcript": "...", "screenshot": "...", "timestamp": "..."}
        """
        action = intent.get("action")
        if not action:
            return {"status": "error", "message": "无法识别指令"}

        module = self.modules.get(action)
        if not module:
            return {"status": "error", "message": f"没有找到能处理 '{action}' 的模块"}

        # 合并 intent params 到 context
        context.update(intent.get("params", {}))

        try:
            result = module.run(context, self.config)
            return result
        except Exception as e:
            return {"status": "error", "message": f"模块执行出错: {e}"}

    def list_modules(self) -> list[dict]:
        return [mod.MANIFEST for mod in self.modules.values()]
