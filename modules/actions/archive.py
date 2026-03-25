"""
modules/actions/archive.py — 归档模块 (Phase 1)
截图 + 备注 → Obsidian md
"""
from datetime import datetime
from pathlib import Path
import shutil

MANIFEST = {
    "name": "archive",
    "triggers": ["记", "保存", "归档", "存档"],
    "description": "截图 + 备注写入 Obsidian vault",
}


def run(context: dict, config: dict) -> dict:
    cfg = config.get("actions", {}).get("archive", {})
    vault = Path(cfg.get("obsidian_vault", "D:/AIproject/aria-vault"))
    folder = cfg.get("target_folder", "captures")

    dt = datetime.now()
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M:%S")
    file_ts = dt.strftime("%Y%m%d_%H%M%S")

    target_dir = vault / folder / date_str
    target_dir.mkdir(parents=True, exist_ok=True)

    # 复制截图到 vault 内
    screenshot_embed = ""
    src = context.get("screenshot")
    if src and Path(src).exists():
        assets_dir = target_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        dest = assets_dir / f"screenshot_{file_ts}.png"
        shutil.copy(src, dest)
        # Obsidian 相对路径嵌入
        screenshot_embed = f"![[assets/screenshot_{file_ts}.png]]"

    note = context.get("note", context.get("transcript", "（无备注）"))
    tags = context.get("tags", [])
    tags_yaml = "\n".join(f"  - {t}" for t in (tags or ["aria", "capture"]))

    md = f"""---
date: {date_str}
time: {time_str}
source: aria
tags:
{tags_yaml}
---

# 📸 {time_str}

> {note}

{screenshot_embed}

---
*ARIA 自动记录 · {date_str} {time_str}*
"""

    md_path = target_dir / f"aria_{file_ts}.md"
    md_path.write_text(md.strip(), encoding="utf-8")
    print(f"[Archive] Saved: {md_path}")

    return {
        "status": "ok",
        "md_path": str(md_path),
        "message": f"记好了，存在 {date_str} 文件夹",
    }
