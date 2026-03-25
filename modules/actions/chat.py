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
    # reply 已经由 intent 层生成，直接用
    reply = context.get("reply", "嗯？")
    message = context.get("message", context.get("transcript", ""))

    # 如果 intent 给了 reply 就直接用，否则调 LLM 生成
    if not reply or reply == "嗯？":
        reply = _ask_llm(message, config)

    return {
        "status": "ok",
        "message": reply,
    }


def _ask_llm(message: str, config: dict) -> str:
    try:
        from openai import OpenAI
        cfg = config.get("intent", {})
        api_key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        base_url = cfg.get("base_url")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)

        persona = config.get("identity", {}).get("persona", {}).get("personality", "你是 ARIA，一个简洁友好的 AI 助手。")
        resp = client.chat.completions.create(
            model=cfg.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": persona + "\n回复控制在1-2句话。"},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Chat] LLM error: {e}")
        return "嗯，我听到了"
