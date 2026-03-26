"""
modules/actions/chat.py — 纯对话模块 (Phase 1)
不需要截图，直接 LLM 回答。
"""
import os

MANIFEST = {
    "name": "chat",
    "triggers": [],
    "description": "纯对话，不操作文件系统",
}


def run(context: dict, config: dict) -> dict:
    reply = context.get("reply", "")
    message = context.get("message", context.get("transcript", ""))

    # intent 给了 reply 且不是占位符，直接用
    if reply and reply not in ("嗯？", "好的", ""):
        return {"status": "ok", "message": reply}

    # 否则调 LLM 生成（带完整 persona）
    reply = _ask_llm(message, context, config)
    return {"status": "ok", "message": reply}


def _ask_llm(message: str, context: dict, config: dict) -> str:
    try:
        from openai import OpenAI
        cfg = config.get("intent", {})
        api_key = cfg.get("api_key") or os.environ.get("ARIA_INTENT_KEY", "")
        base_url = cfg.get("base_url")

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)

        # 优先用 context 里的 system_prompt（含完整 persona）
        system_prompt = context.get("system_prompt") or \
            config.get("identity", {}).get("persona", {}).get("personality",
                "你是 ARIA，一个简洁友好的 AI 助手。回复控制在1-2句话。")

        # 确保回复简短
        if "回复控制" not in system_prompt:
            system_prompt += "\n回复控制在1-2句话，像朋友聊天，不要废话。"

        resp = client.chat.completions.create(
            model=cfg.get("model", "glm-4-flash"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Chat] LLM error: {e}")
        return "嗯，我听到了"
