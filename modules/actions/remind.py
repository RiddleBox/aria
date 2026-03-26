"""
modules/actions/remind.py — 提醒 / 番茄钟模块

支持：
  "提醒我5分钟后喝水"     → 5分钟后 Windows 通知 + ARIA 语音提醒
  "番茄钟25分钟"          → 25分钟工作 + 5分钟休息循环
  "取消提醒"              → 清除所有待触发提醒

依赖：无第三方库（纯标准库 + winmm/win10toast）
"""
import threading
import time
import re
from datetime import datetime

MANIFEST = {
    "name": "remind",
    "triggers": ["提醒", "remind", "定时", "番茄", "pomodoro", "分钟后", "小时后", "待会", "过会"],
    "description": "设置定时提醒或番茄钟，到时间 ARIA 会语音提醒你",
}

# 全局提醒队列
_reminders: list[dict] = []
_lock = threading.Lock()


def run(context: dict, config: dict) -> dict:
    transcript = context.get("transcript", "")
    params = context  # intent 解析的 params 合并进了 context

    # 取消提醒
    if any(k in transcript for k in ["取消", "停止", "cancel"]):
        return _cancel_all()

    # 番茄钟
    if any(k in transcript for k in ["番茄", "pomodoro"]):
        work_min = int(params.get("work_minutes", 25))
        break_min = int(params.get("break_minutes", 5))
        return _start_pomodoro(work_min, break_min, config)

    # 普通提醒：从 params 或 transcript 提取时长和内容
    minutes = _extract_minutes(params, transcript)
    note = params.get("note") or _extract_note(transcript) or "该做你设定的事了"

    if not minutes:
        return {
            "status": "error",
            "message": "没听清楚几分钟，你再说一次？"
        }

    return _set_reminder(minutes, note, config)


def _set_reminder(minutes: float, note: str, config: dict) -> dict:
    """设置一个定时提醒。"""
    remind_id = f"remind_{int(time.time())}"

    def _fire():
        time.sleep(minutes * 60)
        with _lock:
            _reminders[:] = [r for r in _reminders if r["id"] != remind_id]
        _notify(note, config)

    t = threading.Thread(target=_fire, daemon=True)
    t.start()

    with _lock:
        _reminders.append({"id": remind_id, "note": note, "fire_at": time.time() + minutes * 60})

    mins_str = f"{int(minutes)}分钟" if minutes >= 1 else f"{int(minutes * 60)}秒"
    return {
        "status": "ok",
        "message": f"好，{mins_str}后提醒你：{note}",
        "remind_id": remind_id,
    }


def _start_pomodoro(work_min: int, break_min: int, config: dict) -> dict:
    """番茄钟：工作 → 休息 → 循环。"""
    def _run():
        round_num = 1
        while True:
            # 工作阶段
            time.sleep(work_min * 60)
            _notify(f"第{round_num}个番茄结束！休息{break_min}分钟", config)
            # 休息阶段
            time.sleep(break_min * 60)
            _notify(f"休息结束，开始第{round_num + 1}个番茄", config)
            round_num += 1

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {
        "status": "ok",
        "message": f"番茄钟启动，工作{work_min}分钟，休息{break_min}分钟，我来提醒你",
    }


def _cancel_all() -> dict:
    with _lock:
        count = len(_reminders)
        _reminders.clear()
    if count:
        return {"status": "ok", "message": f"取消了{count}个提醒"}
    return {"status": "ok", "message": "没有待触发的提醒"}


def _notify(message: str, config: dict):
    """触发通知：Windows 系统通知 + ARIA 语音。"""
    print(f"[Remind] ⏰ {message}")

    # 语音提醒
    try:
        from modules.identity.voice import speak
        speak(message, config)
    except Exception as e:
        print(f"[Remind] Voice error: {e}")

    # Windows 系统通知（可选，需要 win10toast）
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast("ARIA 提醒", message, duration=5, threaded=True)
    except ImportError:
        pass  # 没装 win10toast 也没关系，语音提醒已经够用
    except Exception:
        pass


def _extract_minutes(params: dict, transcript: str) -> float | None:
    """从 params 或 transcript 提取时长（分钟）。"""
    # 优先从 intent params 读
    if "duration_minutes" in params:
        return float(params["duration_minutes"])
    if "minutes" in params:
        return float(params["minutes"])

    # 从文字提取：支持"5分钟"、"半小时"、"1小时"、"30秒"
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*小时", lambda m: float(m.group(1)) * 60),
        (r"半小时", lambda m: 30.0),
        (r"(\d+(?:\.\d+)?)\s*分钟", lambda m: float(m.group(1))),
        (r"(\d+(?:\.\d+)?)\s*分", lambda m: float(m.group(1))),
        (r"(\d+(?:\.\d+)?)\s*秒", lambda m: float(m.group(1)) / 60),
    ]
    for pattern, converter in patterns:
        m = re.search(pattern, transcript)
        if m:
            return converter(m)
    return None


def _extract_note(transcript: str) -> str:
    """从文字提取提醒内容。"""
    # 去掉时间部分，剩下的就是备注
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*(?:小时|分钟|分|秒)", "", transcript)
    cleaned = re.sub(r"(提醒我|定时|提醒|待会|过会儿?|后)", "", cleaned).strip()
    return cleaned if len(cleaned) > 1 else ""
