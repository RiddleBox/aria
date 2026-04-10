"""
modules/actions/browse.py — 网页搜索模块

## 功能
用户说「帮我查/搜一下 XXX」→ 搜索网页 → LLM 总结 → 语音播报

## 降级链
1. duckduckgo_search（免费，无需 API key，返回结构化摘要）
2. LLM 总结摘要（GLM/Gemini，消耗极低）
   └─ LLM 不可用时 → 直接播报第一条摘要
3. duckduckgo_search 不可用 → 提示用户安装 + 给出搜索链接

## 模块化设计
- 自包含，不依赖其他 action 模块
- 依赖软检测：未安装时给出友好提示，不影响 ARIA 启动
- 移除方式：直接删除此文件，ARIA 自动感知模块消失

## 安装依赖
    pip install duckduckgo-search

## 触发词示例
    "帮我查一下艾尔登法环远古龙打法"
    "搜一下 Python asyncio 怎么用"
    "查一下明天天气"
    "帮我找找这个 Boss 怎么打"
    "browse 深度优先搜索"
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
    "requires": ["duckduckgo-search"],  # 软依赖声明，仅用于提示
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

    # ── Step 1: 检查依赖 ─────────────────────────────────────
    if not _check_deps():
        install_hint = "pip install duckduckgo-search"
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        return {
            "status": "deps_missing",
            "message": f"browse 模块需要先装依赖：{install_hint}，我先给你搜索链接：{search_url}",
            "query": query,
            "install": install_hint,
            "fallback_url": search_url,
        }

    # ── Step 2: 搜索 ─────────────────────────────────────────
    results = _search(query)

    if not results:
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        return {
            "status": "no_results",
            "message": f"没搜到「{query}」的结果，你可以自己看：{search_url}",
            "query": query,
        }

    # 打印完整结果到 console（调试用）
    print(f"\n[Browse] 搜索「{query}」，找到 {len(results)} 条：")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['title']}")
        print(f"     {r['href']}")
        print(f"     {r['body'][:80]}...")

    # ── Step 3: LLM 总结 → 语音播报 ─────────────────────────
    message = _summarize(query, results[:_MAX_FOR_SUMMARY], config)

    return {
        "status": "ok",
        "message": message,
        "query": query,
        "results": results,
        "total": len(results),
    }


# ── 依赖检测 ──────────────────────────────────────────────────

def _check_deps() -> bool:
    """软检测：duckduckgo_search 是否可用。"""
    try:
        import importlib
        importlib.import_module("duckduckgo_search")
        return True
    except ImportError:
        return False


# ── 搜索 ──────────────────────────────────────────────────────

def _search(query: str) -> list[dict]:
    """
    用 duckduckgo_search 搜索，返回结构化结果列表。
    每条结果：{title, href, body}
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            raw = list(ddgs.text(
                query,
                max_results=_MAX_RESULTS,
                # region="cn-zh",  # 中文结果可选开启
            ))

        results = []
        for item in raw:
            results.append({
                "title": item.get("title", ""),
                "href":  item.get("href", ""),
                "body":  item.get("body", ""),
            })
        return results

    except Exception as e:
        print(f"[Browse] Search error: {e}")
        return []


# ── LLM 总结 ──────────────────────────────────────────────────

def _summarize(query: str, results: list[dict], config: dict) -> str:
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

        # 拼搜索摘要上下文
        snippets = []
        for r in results:
            snippets.append(f"- {r['title']}\n  {r['body'][:120]}")
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
        # 降级：直接用第一条摘要
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
    # 去掉语气词结尾
    t = re.sub(r"[吗呢啊嘛哦？?。！!]+$", "", t).strip()
    return t
