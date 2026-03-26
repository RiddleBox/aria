"""
modules/actions/answer.py — 看截图回答问题 (Phase 1)
"""

MANIFEST = {
    "name": "answer",
    "triggers": ["什么", "怎么", "为什么", "解释", "看看", "分析", "帮我看"],
    "description": "用视觉模型分析截图并回答用户问题",
}


def run(context: dict, config: dict) -> dict:
    question = context.get("question", context.get("transcript", ""))
    screenshot = context.get("screenshot")

    # 没有截图时主动截一张
    if not screenshot:
        try:
            from core.perception import Perception
            p = Perception(config, lambda x: None)
            screenshot = p.take_screenshot()
            print(f"[Answer] Auto screenshot: {screenshot}")
        except Exception as e:
            print(f"[Answer] Auto screenshot failed: {e}")

    if not screenshot:
        return {
            "status": "error",
            "message": "截图失败，没办法看",
        }

    from core.intent import answer_with_screenshot
    answer = answer_with_screenshot(question, screenshot, config)

    return {
        "status": "ok",
        "answer": answer,
        "message": answer,
    }
