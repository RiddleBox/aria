"""
core/window_context.py — 当前窗口感知

获取前台窗口标题 + 进程名，判断是否在玩游戏。
结果注入到每次指令的 context，让意图层和模块都能感知"用户在干什么"。

依赖：pywin32（Windows 专用）
安装：pip install pywin32

用法：
    from core.window_context import get_window_context
    ctx = get_window_context()
    # {"window_title": "Cyberpunk 2077", "process_name": "Cyberpunk2077.exe",
    #  "is_game": True, "game_name": "Cyberpunk 2077", "scene": "gaming"}
"""

import re
from typing import Optional

# 已知游戏进程名 → 游戏显示名称（持续补充）
_GAME_PROCESS_MAP: dict[str, str] = {
    # 主机/PC 大作
    "Cyberpunk2077.exe":        "Cyberpunk 2077",
    "witcher3.exe":             "The Witcher 3",
    "RDR2.exe":                 "Red Dead Redemption 2",
    "GTA5.exe":                 "GTA V",
    "eldenring.exe":            "Elden Ring",
    "sekiro.exe":               "Sekiro",
    "darksouls3.exe":           "Dark Souls III",
    "HorizonZeroDawn.exe":      "Horizon Zero Dawn",
    "Cyberpunk2077_launcher.exe": "Cyberpunk 2077",

    # 竞技/网游
    "VALORANT-Win64-Shipping.exe": "VALORANT",
    "LeagueOfLegends.exe":      "League of Legends",
    "CSGO.exe":                 "CS:GO",
    "cs2.exe":                  "Counter-Strike 2",
    "overwatch.exe":            "Overwatch",
    "Overwatch.exe":            "Overwatch",
    "r5apex.exe":               "Apex Legends",
    "FortniteClient-Win64-Shipping.exe": "Fortnite",
    "bf2042.exe":               "Battlefield 2042",

    # 国产/手游模拟
    "YuanShen.exe":             "原神",
    "StarRail.exe":             "崩坏：星穹铁道",
    "ZenlessZoneZero.exe":      "绝区零",
    "DNF.exe":                  "地下城与勇士",
    "MuMuPlayer.exe":           "手游模拟器 (MuMu)",
    "Nox.exe":                  "手游模拟器 (Nox)",
    "LDPlayer.exe":             "手游模拟器 (雷电)",
    "HD-Player.exe":            "手游模拟器 (BlueStacks)",

    # 独立游戏
    "Hades.exe":                "Hades",
    "Hades2.exe":               "Hades II",
    "hollowknight.exe":         "Hollow Knight",
    "Celeste.exe":              "Celeste",
    "Stardew Valley.exe":       "Stardew Valley",
    "StardewValley.exe":        "Stardew Valley",
    "Terraria.exe":             "Terraria",
    "Minecraft.Windows.exe":    "Minecraft",
    "javaw.exe":                "Minecraft (Java)",  # 可能误判，窗口名再确认

    # 游戏平台
    "steam.exe":                None,   # 平台本身不算游戏
    "EpicGamesLauncher.exe":    None,
    "Battle.net.exe":           None,
    "Origin.exe":               None,
    "GOGGalaxy.exe":            None,
}

# 通过窗口标题关键词判断游戏（兜底规则）
_GAME_TITLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"原神", re.I),                     "原神"),
    (re.compile(r"崩坏.星穹铁道", re.I),             "崩坏：星穹铁道"),
    (re.compile(r"绝区零", re.I),                   "绝区零"),
    (re.compile(r"League of Legends", re.I),        "League of Legends"),
    (re.compile(r"VALORANT", re.I),                 "VALORANT"),
    (re.compile(r"Counter-Strike", re.I),           "Counter-Strike"),
    (re.compile(r"Apex Legends", re.I),             "Apex Legends"),
    (re.compile(r"Minecraft", re.I),                "Minecraft"),
    (re.compile(r"Stardew Valley", re.I),           "Stardew Valley"),
    (re.compile(r"Hollow Knight", re.I),            "Hollow Knight"),
    (re.compile(r"Elden Ring", re.I),               "Elden Ring"),
    (re.compile(r"Cyberpunk", re.I),                "Cyberpunk 2077"),
]

# 场景分类（scene 字段）
_WORK_PROCESSES = {
    "code.exe", "cursor.exe", "idea64.exe", "pycharm64.exe",
    "devenv.exe", "sublime_text.exe", "notepad++.exe",
    "WINWORD.EXE", "EXCEL.EXE", "POWERPNT.EXE",
    "chrome.exe", "msedge.exe", "firefox.exe",
    "slack.exe", "Teams.exe", "WeChat.exe", "企业微信.exe",
}


def get_window_context() -> dict:
    """
    获取当前前台窗口信息。

    Returns:
        {
            "window_title": str,      # 窗口标题
            "process_name": str,      # 进程名
            "is_game": bool,          # 是否在玩游戏
            "game_name": str | None,  # 游戏名（is_game=True 时有值）
            "scene": str,             # "gaming" | "working" | "idle" | "unknown"
        }
    """
    result = {
        "window_title": "",
        "process_name": "",
        "is_game": False,
        "game_name": None,
        "scene": "unknown",
    }

    try:
        import win32gui
        import win32process
        import psutil

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        result["window_title"] = title

        # 获取进程名
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            process_name = proc.name()
            result["process_name"] = process_name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = ""

        # 判断是否游戏
        game_name = _detect_game(process_name, title)
        if game_name:
            result["is_game"] = True
            result["game_name"] = game_name
            result["scene"] = "gaming"
        elif process_name.lower() in {p.lower() for p in _WORK_PROCESSES}:
            result["scene"] = "working"
        elif title:
            result["scene"] = "unknown"
        else:
            result["scene"] = "idle"

    except ImportError:
        # pywin32 / psutil 未安装，返回空上下文
        result["scene"] = "unknown"
    except Exception as e:
        print(f"[WindowContext] Error: {e}")

    return result


def _detect_game(process_name: str, window_title: str) -> Optional[str]:
    """检测游戏，返回游戏名或 None。"""
    # 1. 精确匹配进程名
    matched = _GAME_PROCESS_MAP.get(process_name)
    if matched is not None:
        return matched  # None 表示平台进程，非游戏
    if matched == "":
        return None

    # 2. 大小写不敏感进程名匹配
    proc_lower = process_name.lower()
    for key, val in _GAME_PROCESS_MAP.items():
        if key.lower() == proc_lower and val:
            return val

    # 3. 窗口标题关键词匹配（兜底）
    for pattern, name in _GAME_TITLE_PATTERNS:
        if pattern.search(window_title):
            return name

    return None


def describe_scene(ctx: dict) -> str:
    """
    返回一句人类可读的场景描述，注入到 LLM system prompt 里增强意图理解。

    示例：
        "用户当前正在玩 Elden Ring"
        "用户当前正在使用 Chrome"
        "用户当前无活动窗口"
    """
    if ctx.get("is_game"):
        return f"用户当前正在玩 {ctx['game_name']}"
    title = ctx.get("window_title", "")
    proc = ctx.get("process_name", "")
    if title:
        return f"用户当前活动窗口：{title}（{proc}）"
    return "用户当前无活动窗口"
