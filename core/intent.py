"""
core/intent.py — 意图解析 (Phase 1)
GPT-4o 判断：需不需要截图？要做什么？
"""
import json
import os
from typing import Optional


# ── System Prompt ─────────────────────────────────────────────────────────────
# 两个职责：
# 1. 判断是否需要截图（needs_screenshot）
# 2. 解析动作和参数

SYSTEM_PROMPT = """你是 ARIA 的意图解析器。

用户通过语音说了一句话，你需要输出一个 JSON，包含：
1. needs_screenshot: 是否需要捕捉当前屏幕截图来完成这个请求
2. action: 要执行的动作
3. params: 动作参数
4. reply: ARIA 的语音回复（1句话，简短自然）

## 可用 action

- archive: 把当前内容（截图 + 用户备注）归档到文档
- answer: 看截图回答用户问题、分析屏幕内容
- capture: 录制屏幕视频，用户说"录一下"、"录视频"、"帮我录"、"记录这段"、"clip"、"录N秒"等
- convert: 媒体格式转换（视频→GIF）
- remind: 定时提醒或番茄钟，用户说"提醒我X分钟后"、"番茄钟"、"X分钟后叫我"、"定时X分钟"等
- chat: 纯对话，不需要操作文件系统

## needs_screenshot 判断规则

需要截图的情况（只要符合其中一条就截）：
- 用户想记录/保存当前看到的内容 → archive
- 用户问"这是什么"、"这怎么做"、"帮我看"、"解释一下"等指向屏幕的问题 → answer
- 用户说"这个"、"这段"、"刚才"、"现在"等指示词 → answer
- 用户问 ARIA 能不能看到屏幕、看到窗口、看到界面 → answer
- 用户说"帮我解图"、"分析一下"、"看看这个" → answer
- 用户问屏幕上显示的任何内容 → answer

不需要截图的情况：
- 纯聊天、问时间、问天气等明确与屏幕无关的问题
- 用户明确说了要操作的文件路径
- capture 动作（截图由模块内部处理）

## 输出格式（严格 JSON）

{
  "needs_screenshot": true,
  "action": "archive",
  "params": {
    "note": "用户想记录的备注，原话即可",
    "tags": ["game", "design"]
  },
  "reply": "好，帮你记下来了"
}

capture 动作示例：
{
  "needs_screenshot": false,
  "action": "capture",
  "params": {
    "duration": 15,
    "note": "用户想录的内容备注"
  },
  "reply": "好，录15秒"
}

## 时长提取规则（capture 专用）
- 用户说"录10秒" → duration=10
- 用户说"录半分钟" → duration=30
- 用户说"录一分钟" → duration=60
- 用户没说时长 → duration=10（默认）
- reply 里要带上实际时长，如"好，录10秒"

remind 动作示例：
{
  "needs_screenshot": false,
  "action": "remind",
  "params": {
    "duration_minutes": 5,
    "note": "喝水"
  },
  "reply": "好，5分钟后提醒你喝水"
}

番茄钟示例：
{
  "needs_screenshot": false,
  "action": "remind",
  "params": {
    "work_minutes": 25,
    "break_minutes": 5,
    "note": "番茄钟"
  },
  "reply": "番茄钟启动，专注25分钟"
}

## 注意
- reply 要符合 ARIA 的性格（简短、自然、不用敬语）
- 不确定时默认 chat，needs_screenshot=false
"""


def parse_intent(transcript: str, config: dict, persona_prompt: str = "") -> dict:
    """
    解析用户语音意图。
    如果 needs_screenshot=True，调用方负责截图并把路径填入 context。
    """
    provider = config.get("intent", {}).get("provider", "openai")

    if provider == "openai":
        result = _parse_openai(transcript, config, persona_prompt)
    elif provider == "local":
        result = _parse_local(transcript, config)
    else:
        result = _keyword_fallback(transcript)

    print(f"[Intent] action={result.get('action')} screenshot={result.get('needs_screenshot')}")
    return result


def _parse_openai(transcript: str, config: dict, persona_prompt: str) -> dict:
    try:
        from openai import OpenAI
        cfg = config.get("intent", {})
        api_key = cfg.get("api_key") or os.environ.get("ARIA_INTENT_KEY", "")
        base_url = cfg.get("base_url")  # 可选，用于代理/兼容 API
        
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)

        system = (persona_prompt + "\n\n" + SYSTEM_PROMPT) if persona_prompt else SYSTEM_PROMPT

        resp = client.chat.completions.create(
            model=cfg.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=300,
        )
        return json.loads(resp.choices[0].message.content)

    except Exception as e:
        print(f"[Intent] OpenAI error: {e}")
        return _keyword_fallback(transcript)


def _parse_local(transcript: str, config: dict) -> dict:
    try:
        import requests
        url = config.get("intent", {}).get("local_model_url", "http://localhost:11434/api/chat")
        resp = requests.post(url, json={
            "model": config.get("intent", {}).get("local_model", "llama3"),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "stream": False,
            "format": "json",
        }, timeout=30)
        return json.loads(resp.json()["message"]["content"])
    except Exception as e:
        print(f"[Intent] Local model error: {e}")
        return _keyword_fallback(transcript)


def _keyword_fallback(transcript: str) -> dict:
    """LLM 不可用时的关键词兜底。"""
    t = transcript.lower()
    if any(k in t for k in ["记", "保存", "存", "截图", "记录", "归档"]):
        return {
            "needs_screenshot": True,
            "action": "archive",
            "params": {"note": transcript},
            "reply": "好，截图并记录了",
        }
    if any(k in t for k in ["什么", "怎么", "为什么", "解释", "看"]):
        return {
            "needs_screenshot": True,
            "action": "answer",
            "params": {"question": transcript},
            "reply": "让我看看",
        }
    return {
        "needs_screenshot": False,
        "action": "chat",
        "params": {"message": transcript},
        "reply": "嗯？",
    }


def answer_with_screenshot(question: str, screenshot_path: str, config: dict) -> str:
    """
    用视觉模型分析截图并回答问题。
    视觉模型配置独立（vision_model / vision_api_key / vision_base_url）
    """
    try:
        import base64
        from openai import OpenAI
        import cv2
        import numpy as np
        from io import BytesIO
        
        cfg = config.get("intent", {})

        # 视觉模型用独立的 key 和 base_url
        api_key = cfg.get("vision_api_key") or os.environ.get("ARIA_VISION_KEY", "")
        base_url = cfg.get("vision_base_url") or cfg.get("base_url")
        model = cfg.get("vision_model", "glm-4v-flash")

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)

        # 图像预处理：读取并优化图像
        img = cv2.imread(screenshot_path)
        if img is not None:
            # 获取配置参数
            vision_cfg = cfg.get("vision_optimization", {})
            max_width = vision_cfg.get("max_width", 1280)
            max_height = vision_cfg.get("max_height", 720)
            jpeg_quality = vision_cfg.get("jpeg_quality", 75)
            
            # 分辨率优化
            height, width = img.shape[:2]
            if width > max_width or height > max_height:
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), 
                               interpolation=cv2.INTER_AREA)
                print(f"[Intent] Vision image resized: {width}x{height} -> {new_width}x{new_height}")
            
            # 转换为JPEG格式并压缩
            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            img_bytes = buffer.tobytes()
            img_b64 = base64.b64encode(img_bytes).decode()
            
            print(f"[Intent] Vision image optimized: {len(img_bytes)/1024:.1f}KB")
        else:
            # 降级处理：直接读取原文件
            with open(screenshot_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                    }},
                    {"type": "text", "text": question},
                ],
            }],
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Intent] Vision error: {e}")
        return "抱歉，分析截图时出了问题"
