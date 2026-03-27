# ARIA × Godot 对接手册

> 版本：v1.0 · 2026-03-27
> 面向 Godot 开发者，说明如何把 ARIA 的数据接进桌宠形象

---

## 总体设计思路

ARIA 和 Godot 是两个完全独立的进程，通过**事件总线**和**记忆接口**通信。

```
┌─────────────────────────────────┐        ┌─────────────────────────┐
│           ARIA (Python)         │        │      Godot (桌宠形象)    │
│                                 │        │                         │
│  语音 → 意图 → 模块执行          │──────▶│  订阅事件 → 驱动表情/动画  │
│  记忆存储（事实层）               │◀──────│  查询记忆 → 个性化表现    │
│                                 │  WS   │                         │
└─────────────────────────────────┘        └─────────────────────────┘
```

**分工原则：**
- ARIA：**存事实**（发生了什么、说了什么、用户喜好）
- Godot：**表现层**（什么语气、什么表情、什么时候主动开口）

ARIA 不管性格，只管把数据发出去。同一份数据，换不同性格模板，就是不同桌宠。

---

## Part 1：事件总线（实时驱动）

### 1.1 现状

`core/bus.py` 已实现发布/订阅机制，当前为**进程内**通信。
Phase 4 需要在 `main.py` 启动时，额外开一个 WebSocket 服务器，把 bus 事件转发出去。

### 1.2 待实现（Phase 4 改动点）

**文件：`core/ws_bridge.py`（新建）**

```python
# 伪代码，说明意图
import asyncio, websockets, json
from core.bus import bus

async def ws_handler(websocket):
    # Godot 连上来后，把所有 bus 事件转发给它
    def on_event(event_name, data):
        asyncio.run_coroutine_threadsafe(
            websocket.send(json.dumps({"event": event_name, "data": data})),
            loop
        )
    bus.subscribe("*", on_event)
    await websocket.wait_closed()

# main.py 启动时 asyncio.create_task(start_ws_server())
```

**默认端口：`ws://localhost:7437`**（可在 settings.yaml 配置）

### 1.3 事件列表（Godot 订阅这些）

| 事件名 | 触发时机 | payload |
|---|---|---|
| `aria.state_change` | ARIA 状态切换 | `{"state": "idle\|listening\|thinking\|speaking\|working"}` |
| `aria.transcribed` | 语音识别完成 | `{"transcript": "用户说的话"}` |
| `aria.intent_parsed` | 意图解析完成 | `{"action": "chat", "params": {...}}` |
| `aria.action_start` | 模块开始执行 | `{"action": "archive"}` |
| `aria.action_complete` | 模块执行完成 | `{"action": "archive", "result": {...}}` |
| `aria.speaking` | 即将播放语音 | `{"text": "ARIA 说的话"}` |
| `aria.speaking_done` | 语音播放结束 | `null` |
| `aria.skill_not_found` | 没有对应模块 | `{"action": "xxx", "suggestions": [...]}` |
| `aria.screenshot_taken` | 截图完成 | `{"path": "...jpg"}` |

### 1.4 Godot 接入示例（GDScript）

```gdscript
# aria_bridge.gd
extends Node

var ws = WebSocketPeer.new()
const ARIA_URL = "ws://localhost:7437"

func _ready():
    ws.connect_to_url(ARIA_URL)

func _process(delta):
    ws.poll()
    if ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
        while ws.get_available_packet_count():
            var raw = ws.get_packet().get_string_from_utf8()
            var msg = JSON.parse_string(raw)
            _on_aria_event(msg["event"], msg["data"])

func _on_aria_event(event: String, data: Variant):
    match event:
        "aria.state_change":
            AriaPet.set_state(data["state"])   # 驱动动画状态机
        "aria.speaking":
            AriaPet.show_bubble(data["text"])  # 显示文字气泡
        "aria.speaking_done":
            AriaPet.hide_bubble()
        "aria.action_complete":
            _handle_action(data["action"], data.get("result", {}))

func _handle_action(action: String, result: Dictionary):
    match action:
        "archive", "quick_note":
            AriaPet.play_emotion("satisfied")  # 记录完了，满足感
        "remind":
            AriaPet.play_emotion("alert")      # 提醒设置，警觉
        "search":
            AriaPet.play_emotion("thinking")   # 搜索中，思考
```

---

## Part 2：记忆接口（上下文查询）

### 2.1 记忆文件位置

```
D:\AIproject\aria\data\aria_memory.json
```

Godot 启动时读取一次，之后通过 WebSocket 增量更新（Phase 4 实现）。

### 2.2 数据结构

```json
{
  "interactions": [
    {
      "time": "2026-03-27T15:23:00",
      "transcript": "帮我记一下这个Boss弱点",
      "action": "quick_note",
      "result": "记好了",
      "game": "Elden Ring"
    }
  ],
  "facts": {
    "preferred_language": {
      "value": "粤语",
      "updated": "2026-03-27T15:38:00"
    }
  },
  "events": [
    {
      "id": "1733c683",
      "time": "2026-03-27T15:23:00",
      "type": "note",
      "content": "Boss弱点是背刺",
      "game": "Elden Ring",
      "scene": "gaming",
      "metadata": {
        "file": "data/vault/notes/2026-03-27.md"
      }
    }
  ],
  "summary": "近期操作：2026-03-27（Elden Ring中）quick_note：帮我记一下这个Boss弱点"
}
```

### 2.3 各字段用途

| 字段 | Godot 怎么用 |
|---|---|
| `facts` | 用户偏好，决定角色怎么称呼/对待用户 |
| `events` | 最近发生了什么，主动搭话的素材 |
| `interactions` | 最近聊了什么，避免重复/接上下文 |
| `summary` | 快速了解近期状态，可塞进角色的"今日状态" |

### 2.4 event type 说明

| type | 含义 |
|---|---|
| `note` | 用户用语音记录了什么（quick_note） |
| `screenshot` | 截图并归档了 |
| `reminder` | 设置了一个提醒 |
| `chat` | 值得记住的对话 |

---

## Part 3：语音/文字内容分离（待实现）

### 3.1 设计意图

语音说的和文字气泡显示的可以不一样：
- 语音：`"背刺！"` （短、有个性）
- 文字气泡：`"[2026-03-27 · Elden Ring] Boss弱点是背刺"` （有来源，可追溯）

### 3.2 实现方案（Phase 4 改动点）

**ARIA 侧（改动极小）：**

每个模块的 `run()` 返回值加一个可选的 `display` 字段：
```python
return {
    "status": "ok",
    "message": "背刺！",                                     # 语音用
    "display": "[2026-03-27 · Elden Ring] Boss弱点是背刺",  # 文字气泡用
}
```

没有 `display` 时，Godot 回退使用 `message`。

**main.py（一行改动）：**
```python
# 语音用 message
speak(result.get("message") or intent.get("reply"), config)

# 文字气泡用 display（Godot 从 bus 事件里读）
bus.publish("aria.action_complete", {
    "action": action,
    "result": result,
    "display": result.get("display", result.get("message", ""))
})
```

---

## Part 4：状态机参考

ARIA 的状态流转，Godot 对应的动画状态机建议：

```
idle ──[用户说话]──▶ listening ──[识别完]──▶ thinking
  ▲                                              │
  │                                         [执行完]
  └──[语音播完]── speaking ◀──[有回复]──── working
```

| ARIA 状态 | 建议动画 |
|---|---|
| `idle` | 待机循环（轻微呼吸/眨眼） |
| `listening` | 耳朵竖起/专注表情 |
| `thinking` | 思考动作（转眼珠/手指抵嘴） |
| `working` | 操作中（翻书/打字姿势） |
| `speaking` | 嘴巴动/配合文字气泡 |

---

## Part 5：接入检查清单

Godot 项目启动对接时，按顺序检查：

- [ ] ARIA 运行中，确认 `ws://localhost:7437` 可连接
- [ ] 订阅 `aria.state_change`，验证动画状态机切换正常
- [ ] 订阅 `aria.speaking`，验证文字气泡显示
- [ ] 读取 `aria_memory.json`，验证 facts/events 数据结构
- [ ] 测试 `quick_note` → events 写入 → Godot 能读到新事件
- [ ] 实现 `display` 字段支持（语音/文字分离）

---

## 附：当前模块一览

| 模块文件 | 功能 | 状态 |
|---|---|---|
| `modules/actions/chat.py` | 纯对话 | ✅ |
| `modules/actions/answer.py` | 看截图回答问题 | ✅ |
| `modules/actions/archive.py` | 截图 + 归档到 Obsidian | ✅ |
| `modules/actions/capture.py` | 截图/录屏，游戏自动打标签 | ✅ |
| `modules/actions/quick_note.py` | 语音快速记录到今日笔记 | ✅ |
| `modules/actions/remind.py` | 定时提醒 + 番茄钟 | ✅ |
| `modules/actions/search.py` | 搜记忆库和笔记，LLM 自然总结 | ✅ |
| `modules/actions/convert.py` | 视频转 GIF | ✅ |
| `modules/actions/replay_buffer.py` | 游戏录屏回溯 | ⏸ 暂搁置 |

---

*最后更新：2026-03-27 · ARIA v1.4*
