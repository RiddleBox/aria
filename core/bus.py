"""
core/bus.py — 事件总线

模块间通过 bus 通信，Core 不直接依赖具体模块。

## 标准事件定义

### 感知层事件
- `aria.listening`        ARIA 开始录音          payload: None
- `aria.transcribed`      语音转文字完成          payload: {"transcript": str}

### 意图层事件
- `aria.intent_parsed`    意图解析完成            payload: {"action": str, "params": dict, "needs_screenshot": bool}

### 执行层事件
- `aria.action_start`     模块开始执行            payload: {"action": str, "context": dict}
- `aria.action_complete`  模块执行完成            payload: {"action": str, "result": dict}
- `aria.action_error`     模块执行出错            payload: {"action": str, "error": str}

### 输出层事件
- `aria.speaking`         ARIA 开始说话（TTS）     payload: {"text": str}
- `aria.speaking_done`    ARIA 说完了              payload: None
- `aria.screenshot_taken` 截图完成                payload: {"path": str}

### 状态事件（供 Godot 形象层订阅）
- `aria.state_change`     ARIA 状态变化            payload: {"state": str}
                          state 可选值：
                            "idle"       — 待机
                            "listening"  — 正在监听
                            "thinking"   — 正在处理
                            "speaking"   — 正在说话
                            "working"    — 正在执行任务

## Godot 对接说明
Godot 形象层订阅 `aria.state_change` 和 `aria.speaking` 事件，
驱动角色动画和口型同步。接口预留好，Phase 3 直接接入。

示例：
    from core.bus import bus
    bus.subscribe("aria.state_change", lambda p: print(f"State: {p['state']}"))
    bus.publish("aria.state_change", {"state": "listening"})
"""
from typing import Callable, Any
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable):
        """订阅事件。handler(payload) 会在事件发布时被调用。"""
        self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable):
        """取消订阅。"""
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    def publish(self, event: str, payload: Any = None):
        """发布事件，同步通知所有订阅者。"""
        for handler in self._handlers.get(event, []):
            try:
                handler(payload)
            except Exception as e:
                print(f"[Bus] Handler error on event '{event}': {e}")

    def once(self, event: str, handler: Callable):
        """只触发一次的订阅。"""
        def _once(payload):
            handler(payload)
            self.unsubscribe(event, _once)
        self.subscribe(event, _once)


# 全局单例
bus = EventBus()
