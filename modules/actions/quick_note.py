"""
modules/actions/quick_note.py — 快速记录模块

语音说一句 → 立刻写入今天的笔记文件，不打断当前操作。
支持感知当前场景（游戏/工作），自动打上标签。

归档位置：data/vault/notes/YYYY-MM-DD.md
每天一个文件，追加写入，不覆盖。

触发词示例：
    "记一下……"  "帮我记……"  "备忘……"  "note……"
"""

from datetime import datetime
from pathlib import Path

MANIFEST = {
    "name": "quick_note",
    "triggers": ["记一下", "帮我记", "备忘", "记住", "note", "记录一下", "记个事", "提个醒", "记下来"],
    "description": "快速把语音内容记录到今日笔记，自动打上时间和场景标签",
}


def run(context: dict, config: dict) -> dict:
    transcript = context.get("transcript", "").strip()
    if not transcript:
        return {"status": "error", "message": "没听清楚，再说一遍？"}

    # 清理触发词前缀，只保留实际内容
    content = _strip_trigger(transcript)
    if not content:
        return {"status": "error", "message": "内容是空的，说清楚点"}

    # 场景标签
    scene_tag = _get_scene_tag(context)

    # 时间
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    # 写入路径
    cfg = config.get("actions", {}).get("quick_note", {})
    vault_dir = Path(cfg.get("vault_dir",
                     config.get("actions", {}).get("archive", {}).get("vault_dir", "data/vault")))
    notes_dir = vault_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_file = notes_dir / f"{date_str}.md"

    # 构建条目
    entry = f"- {time_str}{scene_tag} {content}\n"

    # 文件不存在时加标题
    if not note_file.exists():
        header = f"# 📝 {date_str} 笔记\n\n"
        note_file.write_text(header, encoding="utf-8")

    # 追加写入
    with note_file.open("a", encoding="utf-8") as f:
        f.write(entry)

    print(f"[QuickNote] Saved: {note_file} → {entry.strip()}")
    return {
        "status": "ok",
        "message": f"记好了",
        "note_file": str(note_file),
        "entry": entry.strip(),
    }


def _strip_trigger(text: str) -> str:
    """去掉触发词前缀，提取实际要记录的内容。"""
    prefixes = [
        "记一下", "帮我记", "帮我记一下", "备忘", "记住",
        "note", "记录一下", "记个事", "提个醒", "记下来",
    ]
    t = text.strip()
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].lstrip("，。, ：:")
            break
    return t.strip()


def _get_scene_tag(context: dict) -> str:
    """根据当前场景返回标签字符串。"""
    if context.get("is_game") and context.get("game_name"):
        return f" 🎮[{context['game_name']}]"
    scene = context.get("scene", "")
    if scene == "working":
        window = context.get("window_title", "")
        short = window[:20] + "…" if len(window) > 20 else window
        return f" 💼[{short}]" if short else ""
    return ""
