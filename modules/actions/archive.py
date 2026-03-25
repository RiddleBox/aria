"""
modules/actions/archive.py — 文档归档模块
把截图/视频/GIF + 备注写入 Obsidian md 文件
"""
from datetime import datetime
from pathlib import Path
import shutil

MANIFEST = {
    "name": "archive",
    "triggers": ["归档", "整理", "存档", "记录到文档"],
    "description": "将截图、视频、GIF 和备注结构化写入 Obsidian 文档",
}


def run(context: dict, config: dict) -> dict:
    cfg = config.get("actions", {}).get("archive", {})
    vault = Path(cfg.get("obsidian_vault", "data/archive"))
    folder = cfg.get("target_folder", "06-DesignAssistant-Feed")
    local_backup = cfg.get("local_backup", True)

    ts = context.get("timestamp", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(ts)
    except:
        dt = datetime.now()

    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M:%S")
    file_ts = dt.strftime("%Y%m%d_%H%M%S")

    # 归档目标目录
    target_dir = vault / folder / date_str
    target_dir.mkdir(parents=True, exist_ok=True)

    # 复制媒体文件到 vault 内
    def copy_asset(src_path: str, prefix: str) -> str | None:
        if not src_path:
            return None
        src = Path(src_path)
        if not src.exists():
            return None
        dest = target_dir / f"{prefix}_{file_ts}{src.suffix}"
        shutil.copy(src, dest)
        # 返回相对 vault 的路径（Obsidian 内部链接用）
        try:
            rel = dest.relative_to(vault)
            return str(rel).replace("\\", "/")
        except:
            return str(dest)

    screenshot_rel = copy_asset(context.get("screenshot"), "screenshot")
    video_rel = copy_asset(context.get("video"), "replay")
    gif_rel = copy_asset(context.get("gif"), "clip")

    note = context.get("note", context.get("transcript", "（无备注）"))

    # 构建 md 内容
    lines = [
        f"---",
        f"date: {date_str}",
        f"time: {time_str}",
        f"source: aria-capture",
        f"tags:",
        f"  - aria",
        f"  - capture",
        f"---",
        f"",
        f"# 📸 记录 · {time_str}",
        f"",
        f"> {note}",
        f"",
    ]

    if screenshot_rel:
        lines += [f"## 截图", f"", f"![[{screenshot_rel}]]", f""]

    if gif_rel:
        lines += [f"## GIF 片段", f"", f"![[{gif_rel}]]", f""]
    elif video_rel:
        lines += [f"## 视频片段", f"", f"[[{video_rel}|▶ 播放]]", f""]

    lines += [
        f"## 备注",
        f"",
        f"> （可在这里补充想法）",
        f"",
        f"---",
        f"*由 Aria 自动记录 · {date_str} {time_str}*",
    ]

    md_content = "\n".join(lines)
    md_path = target_dir / f"aria_capture_{file_ts}.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"[Archive] Saved: {md_path}")

    # 本地备份
    if local_backup:
        local_dir = Path(__file__).parent.parent.parent / "data" / "archive" / date_str
        local_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(md_path, local_dir / md_path.name)

    return {
        "status": "ok",
        "md_path": str(md_path),
        "message": f"已归档到 {folder}/{date_str}/",
    }
