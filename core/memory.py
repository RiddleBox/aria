"""
core/memory.py — ARIA 记忆系统

职责：存事实，不管怎么表现。
Godot 通过 HTTP API（Phase 4）或直接读 JSON 文件拿数据，
用角色性格决定怎么呈现。

## 记忆结构

aria_memory.json
├── interactions[]   近期对话流水（滚动保留最近 N 条，意图解析用）
├── facts{}          用户基本信息 + 偏好（用户自己说的）
├── events[]         重要事件精华（截图、记录、提醒等，Godot 读这里）
└── summary          给 LLM 用的短期摘要（每 20 条 interaction 自动压缩）

## Godot 对接

读取接口（Phase 4 通过 WebSocket/HTTP 暴露，现在可直接读文件）：
- get_facts()        → 用户基本信息和偏好
- get_recent_events(n) → 最近 n 条重要事件
- get_summary()      → 短期摘要文本（可直接塞进 system prompt）
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# 滚动窗口：interactions 最多保留多少条
_MAX_INTERACTIONS = 50
# 触发自动 summary 压缩的阈值
_SUMMARY_TRIGGER = 20


class Memory:
    def __init__(self, data_dir: str = "data"):
        self._path = Path(data_dir) / "aria_memory.json"
        self._data = self._load()

    # ── 内部读写 ──────────────────────────────────────────────

    def _load(self) -> dict:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                # 兼容旧格式（只有 interactions + facts）
                raw.setdefault("events", [])
                raw.setdefault("summary", "")
                return raw
            except Exception as e:
                print(f"[Memory] Load error: {e}, starting fresh")
        return {"interactions": [], "facts": {}, "events": [], "summary": ""}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ── 对话流水（内部用）────────────────────────────────────

    def add_interaction(self, transcript: str, action: str, result: str,
                        context: dict = None):
        """
        记录一次完整交互。
        context 里可以带 window_title / game_name / scene 等窗口上下文。
        """
        entry = {
            "time": datetime.now().isoformat(),
            "transcript": transcript,
            "action": action,
            "result": result,
        }
        # 附加场景信息（有的话）
        if context:
            if context.get("game_name"):
                entry["game"] = context["game_name"]
            elif context.get("scene") == "working":
                entry["window"] = context.get("window_title", "")

        self._data["interactions"].append(entry)

        # 滚动窗口
        if len(self._data["interactions"]) > _MAX_INTERACTIONS:
            self._data["interactions"] = self._data["interactions"][-_MAX_INTERACTIONS:]

        self._save()

        # 达到阈值时自动触发摘要压缩（异步，不阻塞主流程）
        if len(self._data["interactions"]) % _SUMMARY_TRIGGER == 0:
            self._try_compress()

    def get_recent_interactions(self, n: int = 10) -> list[dict]:
        """获取最近 n 条对话，用于意图解析上下文。"""
        return self._data["interactions"][-n:]

    # ── 事件（Godot 主要读这里）──────────────────────────────

    def add_event(self, event_type: str, content: str,
                  metadata: dict = None, context: dict = None):
        """
        记录一个重要事件。

        event_type 可选值：
            "note"       用户说"记一下……"
            "screenshot" 截图归档
            "reminder"   提醒设置
            "chat"       值得记住的对话
            "fact"       用户说了关于自己的信息

        metadata: 额外数据，如 {"file": "...path", "game": "Elden Ring"}
        """
        event = {
            "id": _gen_id(),
            "time": datetime.now().isoformat(),
            "type": event_type,
            "content": content,
        }
        if metadata:
            event["metadata"] = metadata
        if context:
            if context.get("game_name"):
                event["game"] = context["game_name"]
            if context.get("scene"):
                event["scene"] = context["scene"]

        self._data["events"].append(event)

        # events 最多保留 200 条
        if len(self._data["events"]) > 200:
            self._data["events"] = self._data["events"][-200:]

        self._save()
        return event["id"]

    def get_recent_events(self, n: int = 20,
                          event_type: Optional[str] = None) -> list[dict]:
        """
        获取最近 n 条事件。
        event_type 可过滤类型（None = 全部）。
        Godot 调这里拿数据。
        """
        events = self._data["events"]
        if event_type:
            events = [e for e in events if e.get("type") == event_type]
        return events[-n:]

    # ── facts（用户基本信息和偏好）───────────────────────────

    def set_fact(self, key: str, value):
        """
        存储用户说过的信息。
        示例：set_fact("name", "小明") / set_fact("prefers_language", "粤语")
        Godot 读这里驱动角色称呼用户的方式。
        """
        self._data["facts"][key] = {
            "value": value,
            "updated": datetime.now().isoformat(),
        }
        self._save()

    def get_fact(self, key: str, default=None):
        entry = self._data["facts"].get(key)
        if entry is None:
            return default
        return entry["value"]

    def get_facts(self) -> dict:
        """获取所有 facts（供 Godot 读取）。"""
        return {k: v["value"] for k, v in self._data["facts"].items()}

    # ── summary（给 LLM 的上下文摘要）───────────────────────

    def get_summary(self) -> str:
        """
        返回近期摘要文本，可以直接塞进 system prompt。
        Godot 也可以读这个了解"最近发生了什么"。
        """
        return self._data.get("summary", "")

    def set_summary(self, text: str):
        self._data["summary"] = text
        self._save()

    def build_context_prompt(self, n_interactions: int = 6) -> str:
        """
        生成给 LLM 用的上下文字符串，包含：
        - facts（用户信息）
        - 近期对话
        - summary
        """
        parts = []

        facts = self.get_facts()
        if facts:
            fact_lines = "\n".join(f"  - {k}: {v}" for k, v in facts.items())
            parts.append(f"【关于用户】\n{fact_lines}")

        summary = self.get_summary()
        if summary:
            parts.append(f"【近期摘要】\n{summary}")

        recent = self.get_recent_interactions(n_interactions)
        if recent:
            lines = []
            for r in recent:
                game = f" [{r['game']}]" if r.get("game") else ""
                lines.append(f"  用户{game}：{r['transcript']}")
                lines.append(f"  ARIA：{r['result']}")
            parts.append("【近期对话】\n" + "\n".join(lines))

        return "\n\n".join(parts)

    # ── facts 自动提取 ────────────────────────────────────────

    def auto_extract_facts(self, transcript: str) -> dict:
        """
        从用户说的一句话里自动提取 facts 并写入。
        返回本次新写入的 {key: value}（空 dict 表示没有提取到）。

        调用时机：main.py 每次交互后调用（写 interaction 之后）。
        零 token，不阻塞主流程。
        """
        new_facts = extract_facts(transcript)
        if not new_facts:
            return {}

        written = {}
        for key, value in new_facts.items():
            # preferences 类累积追加（不覆盖），其余覆盖
            if key == "preferences":
                existing = self.get_fact("preferences") or []
                if isinstance(existing, str):
                    existing = [existing]
                if value not in existing:
                    existing.append(value)
                    self.set_fact("preferences", existing)
                    written[key] = value
            else:
                old = self.get_fact(key)
                if old != value:
                    self.set_fact(key, value)
                    written[key] = value

        if written:
            print(f"[Memory] Auto facts: {written}")
        return written

    def _try_compress(self):
        """
        将旧的 interactions 压缩成 summary（简单版：取最近几条关键内容）。
        生产环境可以改成调 LLM 生成摘要，现在用规则兜底。
        """
        interactions = self._data["interactions"]
        if len(interactions) < _SUMMARY_TRIGGER:
            return

        # 取非 chat 的动作作为摘要要点
        notable = [i for i in interactions[-_SUMMARY_TRIGGER:]
                   if i.get("action") not in ("chat",)]
        if not notable:
            return

        lines = []
        for n in notable[-5:]:
            t = n["time"][:10]
            game = f"（{n['game']}中）" if n.get("game") else ""
            lines.append(f"{t}{game} {n['action']}：{n['transcript'][:30]}")

        self._data["summary"] = "近期操作：" + "；".join(lines)
        self._save()
        print(f"[Memory] Summary updated: {self._data['summary']}")


def _gen_id() -> str:
    """生成简短唯一 ID。"""
    import hashlib, time
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:8]


# ── Facts 自动提取（规则层）────────────────────────────────────────────────────

import re

# 规则表：(pattern, fact_key, value_group_index)
# value_group_index=0 → 用捕获组1的内容；=-1 → 固定值（见下方 FIXED_FACTS）
_FACT_RULES: list[tuple] = [
    # 姓名：只匹配「我叫/我名字是/我名字叫」，不包含「叫我」（那个走 FIXED_FACT_RULES）
    (r"我(叫|名字是|名字叫)\s*([^\s，。？！,\.]{1,8})", "name", 2),

    # 偏好语言
    (r"(用|说|讲)\s*(粤语|广东话|普通话|英文|英语|日语|日文)", "preferred_language", 2),
    (r"我(比较)?喜欢(说|用|讲)\s*(粤语|广东话|普通话|英文|英语|日语|日文)", "preferred_language", 3),

    # 游戏偏好：「在玩」后面不能含「在」「住」「位于」等地点词
    (r"我(最近|现在|正在)?在?玩的?\s*([^\s，。？！,\.在住位于]{2,10}?)(?:这个|这款)?(?:游戏)?(?:\s|$|[，。？！])", "current_game", 2),
    (r"我喜欢玩\s*([^\s，。？！,\.]{2,10})", "fav_game", 1),

    # 职业 / 身份
    (r"我是(一?(名|个))?\s*(程序员|开发者|设计师|游戏策划|学生|上班族|自由职业者|产品经理|运营|美术|音效师)", "occupation", 3),

    # 地区：只匹配「住在/居住在/位于」，避免被「在玩」误触发
    (r"我(住在|居住在|位于)\s*([^\s，。？！,\.]{2,6})", "location", 2),

    # 喜好/厌恶（通用，排除游戏动词）
    (r"我(不|很|非常|挺|比较)?(喜欢|讨厌|痛恨|爱|害怕)\s*(?!玩)([^\s，。？！,\.]{2,15})", "preferences", 0),
]

# 固定值规则：命中后直接写 key=value
_FIXED_FACT_RULES: list[tuple] = [
    (r"(不要|别)\s*(说|用)\s*敬语", "no_honorifics", True),
    (r"(叫我|称呼我)\s*(哥|姐|大哥|老哥|老姐|老板|老大)", "address_style", "兄弟称呼"),
]


def extract_facts(transcript: str) -> dict[str, str]:
    """
    从一句话里用规则提取 facts，返回 {key: value} 字典。
    零 token 消耗，高置信度优先。
    可能返回空 dict（没匹配到任何规则）。
    """
    found: dict[str, str] = {}

    # 固定值规则
    for pattern, key, value in _FIXED_FACT_RULES:
        if re.search(pattern, transcript):
            found[key] = value

    # 捕获组规则
    for pattern, key, group_idx in _FACT_RULES:
        m = re.search(pattern, transcript)
        if not m:
            continue

        if group_idx == 0:
            # preferences 类：用整个匹配串作为值
            value = m.group(0).strip()
        else:
            try:
                value = m.group(group_idx)
            except IndexError:
                continue

        if value and value.strip():
            found[key] = value.strip()

    return found


# 全局单例（和 bus 一样）
_instance: Optional[Memory] = None


def get_memory(data_dir: str = "data") -> Memory:
    global _instance
    if _instance is None:
        _instance = Memory(data_dir)
    return _instance
