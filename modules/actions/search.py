"""
modules/actions/search.py — 记忆库搜索模块

从两个来源搜索：
1. aria_memory.json → events / interactions（结构化记忆）
2. data/vault/notes/*.md → 快速记录的笔记文件（文本）

不依赖外部库，纯关键词匹配，零 token 消耗。
有结果时语音播报前 N 条，同时在 console 打印完整列表。

触发词示例：
    "找一下我之前记的 Boss 弱点"
    "搜一下提醒"
    "我之前说过什么关于原神的"
    "找找我记过什么"
"""

import re
from pathlib import Path
from datetime import datetime

MANIFEST = {
    "name": "search",
    "triggers": ["找一下", "搜一下", "找找", "搜索", "查一下我之前", "我之前说过", "我记过", "search", "找我之前"],
    "description": "在记忆库和笔记文件中搜索关键词，语音播报结果",
}

# 语音播报最多几条（太多会很啰嗦）
_MAX_VOICE_RESULTS = 3


def run(context: dict, config: dict) -> dict:
    transcript = context.get("transcript", "")
    query = _extract_query(transcript)

    if not query:
        return {"status": "error", "message": "要搜什么？说清楚点"}

    results = []

    # 1. 搜结构化记忆（events + interactions）
    results += _search_memory(query, context)

    # 2. 搜笔记文件（vault/notes/*.md）
    results += _search_notes(query, config)

    if not results:
        return {
            "status": "ok",
            "message": f"没找到关于「{query}」的记录",
            "query": query,
            "results": [],
        }

    # 按时间降序排列（最近的在前）
    results.sort(key=lambda r: r.get("time", ""), reverse=True)

    # 打印完整结果到 console
    print(f"\n[Search] 搜索「{query}」，找到 {len(results)} 条：")
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r['source']}] {r['time'][:10]} — {r['content'][:60]}")

    # 语音播报：用 LLM 自然总结（结果短+限token，消耗极低）
    voice_results = results[:_MAX_VOICE_RESULTS]
    message = _summarize(query, voice_results, len(results), config)

    return {
        "status": "ok",
        "message": message,
        "query": query,
        "results": results,
        "total": len(results),
    }


def _search_memory(query: str, context: dict) -> list[dict]:
    """搜索 aria_memory.json 中的 events 和 interactions。"""
    results = []
    try:
        from core.memory import get_memory
        memory = get_memory()

        keywords = _tokenize(query)

        # 搜 events（重要事件，优先级高）
        for event in memory.get_recent_events(200):
            content = event.get("content", "")
            if _match(content, keywords):
                results.append({
                    "source": "事件记录",
                    "time": event.get("time", ""),
                    "content": content,
                    "type": event.get("type", ""),
                    "game": event.get("game", ""),
                    "metadata": event.get("metadata", {}),
                })

        # 搜 interactions（对话流水）
        for item in memory.get_recent_interactions(50):
            text = item.get("transcript", "")
            if _match(text, keywords):
                results.append({
                    "source": "对话记录",
                    "time": item.get("time", ""),
                    "content": text,
                    "type": "interaction",
                    "game": item.get("game", ""),
                    "metadata": {},
                })

    except Exception as e:
        print(f"[Search] Memory search error: {e}")

    return results


def _search_notes(query: str, config: dict) -> list[dict]:
    """搜索 vault/notes/*.md 笔记文件。"""
    results = []
    try:
        cfg = config.get("actions", {}).get("archive", {})
        vault_dir = Path(cfg.get("vault_dir", "data/vault"))
        notes_dir = vault_dir / "notes"

        if not notes_dir.exists():
            return []

        keywords = _tokenize(query)

        for md_file in sorted(notes_dir.glob("*.md"), reverse=True):
            try:
                text = md_file.read_text(encoding="utf-8")
                lines = text.splitlines()
                for line in lines:
                    # 跳过标题行
                    if line.startswith("#") or not line.strip():
                        continue
                    if _match(line, keywords):
                        # 从文件名提取日期，从行内容提取时间
                        date_str = md_file.stem  # "2026-03-27"
                        time_match = re.match(r"- (\d{2}:\d{2})", line)
                        time_str = time_match.group(1) if time_match else "00:00"
                        results.append({
                            "source": "笔记",
                            "time": f"{date_str}T{time_str}:00",
                            "content": line.lstrip("- ").strip(),
                            "type": "note",
                            "game": "",
                            "metadata": {"file": str(md_file)},
                        })
            except Exception:
                continue

    except Exception as e:
        print(f"[Search] Notes search error: {e}")

    return results


def _extract_query(transcript: str) -> str:
    """从语音文本中提取搜索关键词，去掉触发词前缀。"""
    prefixes = [
        "找一下我之前记的", "找一下我之前说的", "找一下",
        "搜一下", "搜索", "查一下我之前", "查一下",
        "我之前说过什么关于", "我之前说过",
        "我记过什么关于", "我记过",
        "找找", "search",
        "找我之前记的", "找我之前",
    ]
    t = transcript.strip()
    for p in sorted(prefixes, key=len, reverse=True):  # 先匹配长的
        if t.startswith(p):
            t = t[len(p):].lstrip("，。, ：:的 ")
            break
    # 去掉语气词结尾
    t = re.sub(r"[吗呢啊嘛哦？?。！!]+$", "", t).strip()
    return t


def _tokenize(query: str) -> list[str]:
    """简单分词：按空格/标点切分，过滤单字停用词。"""
    stopwords = {"的", "了", "吗", "呢", "啊", "是", "有", "在", "我", "你", "他", "她"}
    tokens = re.split(r"[\s，。、,.]+", query)
    tokens = [t for t in tokens if len(t) >= 2 and t not in stopwords]
    # 如果切完没词了，就用原始 query 整体匹配
    return tokens if tokens else [query]


def _match(text: str, keywords: list[str]) -> bool:
    """任意一个关键词命中就算匹配（OR 逻辑）。"""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _summarize(query: str, results: list[dict], total: int, config: dict) -> str:
    """
    用 LLM 把搜索结果总结成一句自然语言。
    失败时降级为规则拼接，不影响主流程。
    """
    try:
        import os
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

        # 把结果拼成简短上下文
        lines = []
        for r in results:
            date = r["time"][:10]
            game = f"（{r['game']}中）" if r.get("game") else ""
            lines.append(f"- {date}{game}：{r['content'][:50]}")

        context_text = "\n".join(lines)
        more = f"（共{total}条，只展示最近{len(results)}条）" if total > len(results) else f"（共{total}条）"

        prompt = f"""用户搜索了「{query}」，找到了以下记录{more}：
{context_text}

用1-2句话，以 ARIA 的口吻，自然地告诉用户找到了什么。简短，不废话，不要逐条念。"""

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 ARIA，简洁直接，像朋友说话，不用敬语。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=80,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Search] Summarize fallback: {e}")
        # 降级：规则拼接
        if total == 0:
            return f"没找到关于「{query}」的记录"
        if total == 1:
            return f"找到1条：{results[0]['content'][:40]}"
        lines = [f"{r['time'][:10]}，{r['content'][:25]}" for r in results]
        return f"找到{total}条，最近的：{'；'.join(lines)}"
