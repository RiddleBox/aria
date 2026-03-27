"""
core/skill_finder.py — 能力发现模块

当 Dispatcher 找不到对应模块时调用。
在 PyPI 和 GitHub 搜索可能满足该能力的资源，
返回推荐列表和安装说明，告诉用户去哪里找、放到哪里。

设计原则：
- 不自动安装任何东西，用户保持完全控制权
- 尽量不消耗 token（优先走 API 搜索，不走 LLM）
- 结果是人类可读的建议，用户下载放入指定目录后 Dispatcher 自动发现
"""

import json
import urllib.request
import urllib.parse
from typing import Optional

# 模块名 → 推荐资源的静态映射（覆盖高频场景，零 token 消耗）
# 格式：action_name → list of {name, source, url, install_hint, description}
_STATIC_CATALOG: dict[str, list[dict]] = {
    "remind": [
        {
            "name": "schedule",
            "source": "PyPI",
            "url": "https://pypi.org/project/schedule/",
            "install_hint": "pip install schedule",
            "description": "轻量定时任务库，适合做\"提醒我 X 点做 Y\"",
        },
        {
            "name": "plyer",
            "source": "PyPI",
            "url": "https://pypi.org/project/plyer/",
            "install_hint": "pip install plyer",
            "description": "跨平台系统通知，Windows 原生气泡提醒",
        },
    ],
    "browse": [
        {
            "name": "playwright",
            "source": "PyPI",
            "url": "https://pypi.org/project/playwright/",
            "install_hint": "pip install playwright && playwright install chromium",
            "description": "完整浏览器自动化，适合需要登录/交互的网页",
        },
        {
            "name": "readability-lxml",
            "source": "PyPI",
            "url": "https://pypi.org/project/readability-lxml/",
            "install_hint": "pip install requests readability-lxml",
            "description": "轻量网页正文提取，适合\"帮我读一下这篇文章\"",
        },
    ],
    "search": [
        {
            "name": "ripgrep (rg)",
            "source": "GitHub",
            "url": "https://github.com/BurntSushi/ripgrep/releases",
            "install_hint": "下载 rg.exe 放到 PATH 目录",
            "description": "极速本地文件搜索，适合搜 Obsidian vault",
        },
    ],
    "read": [
        {
            "name": "pymupdf",
            "source": "PyPI",
            "url": "https://pypi.org/project/PyMuPDF/",
            "install_hint": "pip install pymupdf",
            "description": "PDF 文本提取，适合\"帮我读一下这个 PDF\"",
        },
    ],
    "translate": [
        {
            "name": "deep-translator",
            "source": "PyPI",
            "url": "https://pypi.org/project/deep-translator/",
            "install_hint": "pip install deep-translator",
            "description": "多引擎翻译（Google/DeepL/Bing），免费额度够用",
        },
    ],
    "music": [
        {
            "name": "yt-dlp",
            "source": "PyPI",
            "url": "https://pypi.org/project/yt-dlp/",
            "install_hint": "pip install yt-dlp",
            "description": "音视频下载，支持 YouTube/B站等",
        },
    ],
    "weather": [
        {
            "name": "requests (wttr.in)",
            "source": "PyPI",
            "url": "https://wttr.in",
            "install_hint": "pip install requests  # 调用 wttr.in 免费 API，无需 key",
            "description": "查天气，直接调 wttr.in，不需要注册",
        },
    ],
}

# 模块目录提示（用户放文件的位置）
_MODULES_DIR_HINT = "modules/actions/"


def find(action: str, transcript: Optional[str] = None) -> dict:
    """
    根据 action 名称（和可选的原始语音文本）查找推荐资源。

    Returns:
        {
            "found": bool,
            "action": str,
            "suggestions": [...],   # 推荐列表
            "message": str,         # 人类可读的回复
            "modules_dir": str,     # 告诉用户放哪
        }
    """
    suggestions = []

    # 1. 先查静态目录（零消耗）
    if action in _STATIC_CATALOG:
        suggestions = _STATIC_CATALOG[action]

    # 2. 静态没命中 → 去 PyPI 搜索（网络请求，无 token 消耗）
    if not suggestions:
        suggestions = _search_pypi(action)

    if not suggestions:
        return {
            "found": False,
            "action": action,
            "suggestions": [],
            "message": f"我还没有「{action}」这个能力，也没找到现成的包。你可以把相关 Python 脚本放到 {_MODULES_DIR_HINT}，实现 MANIFEST + run() 接口就能自动加载。",
            "modules_dir": _MODULES_DIR_HINT,
        }

    message = _format_message(action, suggestions)
    return {
        "found": True,
        "action": action,
        "suggestions": suggestions,
        "message": message,
        "modules_dir": _MODULES_DIR_HINT,
    }


def _search_pypi(query: str, max_results: int = 3) -> list[dict]:
    """调用 PyPI JSON API 搜索，返回候选列表。"""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://pypi.org/pypi/{encoded}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "ARIA-skill-finder/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            info = data.get("info", {})
            return [{
                "name": info.get("name", query),
                "source": "PyPI",
                "url": info.get("project_url") or f"https://pypi.org/project/{info.get('name', query)}/",
                "install_hint": f"pip install {info.get('name', query)}",
                "description": (info.get("summary") or "")[:80],
            }]
    except Exception:
        pass

    # 精确包名没找到，fallback 到搜索页（不解析，只给链接）
    try:
        encoded = urllib.parse.quote(query)
        search_url = f"https://pypi.org/search/?q={encoded}"
        return [{
            "name": f"搜索结果（{query}）",
            "source": "PyPI Search",
            "url": search_url,
            "install_hint": "—",
            "description": f"在 PyPI 搜索与「{query}」相关的包",
        }]
    except Exception:
        return []


def _format_message(action: str, suggestions: list[dict]) -> str:
    """生成人类可读的推荐消息。"""
    lines = [f"我还没有「{action}」这个能力，但找到了一些可以用的方案：\n"]
    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. **{s['name']}** ({s['source']})")
        lines.append(f"   {s['description']}")
        lines.append(f"   安装：`{s['install_hint']}`")
        lines.append(f"   链接：{s['url']}")
        lines.append("")
    lines.append(f"下载/安装后，把模块文件放到 `{_MODULES_DIR_HINT}`，实现 `MANIFEST` + `run()` 接口，我下次就能自动识别到。")
    lines.append(f"\n需要我帮你写一个模块模板吗？")
    return "\n".join(lines)
