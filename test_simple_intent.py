#!/usr/bin/env python3
"""
简单意图解析测试 - 测试关键词兜底功能
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.intent import _keyword_fallback

def test_keyword_fallback():
    """测试关键词兜底功能"""
    
    print("=== 关键词兜底功能测试 ===")
    
    test_cases = [
        "帮我截图看看",
        "截个图",
        "看看屏幕内容", 
        "记录当前画面",
        "这是什么",
        "怎么操作",
        "你好",
        "今天天气怎么样"
    ]
    
    for command in test_cases:
        print(f"\n指令: {command!r}")
        result = _keyword_fallback(command)
        print(f"  需要截图: {result['needs_screenshot']}")
        print(f"  动作: {result['action']}")
        print(f"  回复: {result['reply']}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_keyword_fallback()