"""
modules/actions/browse.py — 网页搜索模块

## 功能
用户说「帮我查/搜一下 XXX」→ 搜索网页 → LLM 总结 → 语音播报

## 降级链（运行时动态探测，不硬编码）
① ddgs 搜索 + LLM 总结（ddgs 包可用时）
② GLM 联网搜索（ddgs 不可用 / 无结果时，需要 ARIA_INTENT_KEY）
③ 兜底：返回 DuckDuckGo 搜索链接，让用户自己查

## 模块化设计
- 自包含，不依赖其他 action 模块
- 依赖软检测：未安装时给出友好提示，不影响 ARIA 启动
- 移除方式：直接删除此文件，ARIA 自动感知模块消失

## 安装依赖（可选，有降级链）
    pip install ddgs
"""

import re
import os
from typing import Optional

MANIFEST = {
    "name": "browse",
    "triggers": [
        "帮我查", "帮我搜", "查一下", "搜一下网页",
        "帮我找找", "上网查", "上网搜", "查查",
        "browse", "google", "搜网页",
    ],
    "description": "搜索互联网，用 LLM 总结结果后语音播报",
    "requires": ["ddgs"],  # 软依赖声明，仅用于提示
}

# 搜索结果取前几条喂给 LLM
_MAX_RESULTS = 5
# LLM 总结最多用几条（节省 token）
_MAX_FOR_SUMMARY = 3


def run(context: dict, config: dict) -> dict:
    transcript = context.get("transcript", "")
    query = _extract_query(transcript)

    if not query:
        return {"status": "error", "message": "查什么？说清楚点"}

    # ── 降级链 ───────────────────────────────────────────────
    # ① 尝试 ddgs 搜索
    results = []
    if _check_ddgs():
        results = _search_ddgs(query)

    # ② ddgs 不可用或无结果 → GLM 联网搜索
    if not results:
        glm_answer = _search_glm(query, config)
        if glm_answer:
            return {
                "status": "ok",
                "message": glm_answer,
                "query": query,
                "source": "glm-web",
            }

    # ③ 兜底：给链接
    if not results:
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        hint = "ddgs 不可用" if not _check_ddgs() else "搜索无结果"
        return {
            "status": "no_results",
            "message": f"{hint}，你可以自己看：{search_url}",
            "query": query,
            "fallback_url": search_url,
        }

    # 打印完整结果（调试用）
    print(f"\n[Browse] 搜索「{query}」，找到 {len(results)} 条：")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['title']}")
        print(f"     {r['href']}")
        print(f"     {r['body'][:80]}...")

    # ── LLM 总结 → 语音播报 ──────────────────────────────────
    message = _summarize_with_llm(query, results[:_MAX_FOR_SUMMARY], config)

    return {
        "status": "ok",
        "message": message,
        "query": query,
        "results": results,
        "total": len(results),
        "source": "ddgs",
    }


# ── 依赖检测 ──────────────────────────────────────────────────

def _check_ddgs() -> bool:
    """软检测：ddgs 是否可用。"""
    try:
        import importlib
        importlib.import_module("ddgs")
        return True
    except ImportError:
        return False


# ── 搜索（ddgs）──────────────────────────────────────────────

def _search_ddgs(query: str) -> list[dict]:
    """
    用 ddgs 搜索，返回结构化结果列表。
    每条结果：{title, href, body}
    """
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            raw = list(ddgs.text(
                query,
                max_results=_MAX_RESULTS,
            ))

        return [
            {"title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")}
            for r in raw
        ]
    except Exception as e:
        print(f"[Browse] ddgs search error: {e}")
        return []


# ── 搜索（GLM 联网，降级 ②）────────────────────────────────

def _search_glm(query: str, config: dict) -> Optional[str]:
    """
    用 GLM-4 联网搜索功能直接回答。
    GLM 支持 web_search tool，不需要额外包。
    失败时返回 None（继续降级）。
    """
    try:
        from openai import OpenAI

        cfg = config.get("intent", {})
        api_key = cfg.get("api_key") or os.environ.get("ARIA_INTENT_KEY", "")
        base_url = cfg.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        model = cfg.get("model", "glm-4-flash")

        if not api_key:
            return None

        client = OpenAI(api_key=api_key, base_url=base_url)

        # GLM-4 联网搜索：传入 web_search tool
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 ARIA，简洁直接，不废话。回答控制在 1-2 句话。"},
                {"role": "user", "content": f"帮我查一下：{query}"},
            ],
            tools=[{"type": "web_search", "web_search": {"search_query": query, "search_result": True}}],
            max_tokens=150,
            temperature=0.3,
        )

        answer = resp.choices[0].message.content
        if answer and answer.strip():
            print(f"[Browse] GLM web search answer: {answer[:80]}...")
            return answer.strip()
        return None

    except Exception as e:
        print(f"[Browse] GLM web search error: {e}")
        return None


# ── LLM 总结（ddgs 结果精炼）────────────────────────────────

def _summarize_with_llm(query: str, results: list[dict], config: dict) -> str:
    """
    把搜索摘要列表用 LLM 浓缩成 1-2 句语音播报文本。
    失败时降级为直接返回第一条摘要。
    """
    try:
        from openai import OpenAI

        cfg = config.get("intent", {})
        api_key = cfg.get("api_key") or os.environ.get("ARIA_INTENT_KEY", "")
        base_url = cfg.get("base_url")
        model = cfg.get("model", "glm-4-flash")

        if not api_key:
            raise ValueError("no api_key")

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)

        snippets = [f"- {r['title']}\n  {r['body'][:120]}" for r in results]
        context_text = "\n".join(snippets)

        prompt = (
            f"用户问：「{query}」\n\n"
            f"以下是网页搜索结果：\n{context_text}\n\n"
            "根据以上内容，用 1-2 句话回答用户的问题。"
            "语气简洁自然，像朋友说话，不用敬语，不说「根据搜索结果」之类的废话。"
            "如果信息不足，直接说不确定。"
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 ARIA，简洁直接，不废话。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Browse] Summarize fallback: {e}")
        if results:
            first = results[0]
            return f"{first['title']}：{first['body'][:60]}"
        return f"搜到了但总结失败，你自己搜搜「{query}」"


# ── 关键词提取 ────────────────────────────────────────────────

def _extract_query(transcript: str) -> str:
    """从语音文本里去掉触发词前缀，提取搜索关键词。"""
    prefixes = [
        "帮我查一下", "帮我搜一下", "帮我找找",
        "帮我查", "帮我搜",
        "查一下", "搜一下网页", "搜一下",
        "上网查", "上网搜", "查查",
        "搜网页", "google", "browse",
    ]
    t = transcript.strip()
    for p in sorted(prefixes, key=len, reverse=True):
        if t.lower().startswith(p.lower()):
            t = t[len(p):].lstrip("，。, ：: ")
            break
    t = re.sub(r"[吗呢啊嘛哦？?。！!]+$", "", t).strip()
    return t
