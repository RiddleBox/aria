"""
modules/actions/answer.py — 看截图回答问题 (Phase 1)
"""

MANIFEST = {
    "name": "answer",
    "triggers": ["什么", "怎么", "为什么", "解释"],
    "description": "用 GPT-4o Vision 分析截图并回答用户问题",
}


def run(context: dict, config: dict) -> dict:
    question = context.get("question", context.get("transcript", ""))
    screenshot = context.get("screenshot")

    if not screenshot:
        return {
            "status": "error",
            "message": "没有截图，没办法看",
        }

    from core.intent import answer_with_screenshot
    answer = answer_with_screenshot(question, screenshot, config)

    return {
        "status": "ok",
        "answer": answer,
        "message": answer,  # 直接语音播报
    }
