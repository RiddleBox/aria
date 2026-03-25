"""
core/intent.py — 意图解析引擎
把用户的自然语言转换成结构化的 {"action": "...", "params": {...}}
"""
import json
import os
from typing import Optional


SYSTEM_PROMPT = """你是 Aria 的意图解析器。
用户会用自然语言说一些指令，你需要把它解析成 JSON 格式。

可用的 action 列表：
- capture: 截图或录制屏幕片段（关键词：记录、截图、录一下、保存这段）
- archive: 把内容归档到文档系统（关键词：记录、整理、存档、归类）
- convert: 媒体格式转换（关键词：转成gif、转换、压缩）
- chat: 普通对话（没有明确任务意图时）

输出格式（严格 JSON，不要加其他内容）：
{
  "action": "capture",
  "params": {
    "note": "用户想记录的备注内容",
    "duration_before": 15,
    "duration_after": 5,
    "make_gif": false
  },
  "reply": "好的，帮你记下来了"
}

注意：
- reply 是 Aria 要说给用户听的话，简短自然，1句话
- 如果是 chat，params 可以为空，reply 直接回答用户
- 不确定意图时默认 chat
"""


def parse_intent(transcript: str, config: dict, persona_context: str = "") -> dict:
    """
    解析用户语音转文字的意图。
    返回：{"action": str, "params": dict, "reply": str}
    """
    provider = config.get("intent", {}).get("provider", "openai")

    if provider == "openai":
        return _parse_openai(transcript, config, persona_context)
    elif provider == "local":
        return _parse_local(transcript, config, persona_context)
    else:
        # 降级：简单关键词匹配
        return _parse_keyword(transcript)


def _parse_openai(transcript: str, config: dict, persona_context: str) -> dict:
    try:
        from openai import OpenAI
        intent_cfg = config.get("intent", {})
        api_key = intent_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        client = OpenAI(api_key=api_key)

        system = SYSTEM_PROMPT
        if persona_context:
            system = persona_context + "\n\n" + SYSTEM_PROMPT

        resp = client.chat.completions.create(
            model=intent_cfg.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[Intent] OpenAI parse failed: {e}")
        return _parse_keyword(transcript)


def _parse_local(transcript: str, config: dict, persona_context: str) -> dict:
    """使用本地 Ollama 模型解析意图。"""
    try:
        import requests
        url = config.get("intent", {}).get("local_model_url", "http://localhost:11434/api/chat")
        payload = {
            "model": "llama3",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "stream": False,
            "format": "json",
        }
        resp = requests.post(url, json=payload, timeout=30)
        return json.loads(resp.json()["message"]["content"])
    except Exception as e:
        print(f"[Intent] Local model parse failed: {e}")
        return _parse_keyword(transcript)


def _parse_keyword(transcript: str) -> dict:
    """兜底：简单关键词匹配。"""
    t = transcript.lower()
    if any(k in t for k in ["记", "截图", "录", "保存"]):
        make_gif = any(k in t for k in ["gif", "动图"])
        return {
            "action": "capture",
            "params": {"note": transcript, "make_gif": make_gif},
            "reply": "好，帮你记下来了",
        }
    if any(k in t for k in ["转换", "转成", "gif"]):
        return {
            "action": "convert",
            "params": {"note": transcript},
            "reply": "正在转换",
        }
    return {
        "action": "chat",
        "params": {},
        "reply": "嗯？",
    }
