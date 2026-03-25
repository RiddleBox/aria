"""
core/bus.py — 事件总线
模块间通过 bus 通信，Core 不直接依赖具体模块。
"""
from typing import Callable, Any
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable):
        self._handlers[event].append(handler)

    def publish(self, event: str, payload: Any = None):
        for handler in self._handlers.get(event, []):
            try:
                handler(payload)
            except Exception as e:
                print(f"[Bus] Handler error on event '{event}': {e}")


# 全局单例
bus = EventBus()
