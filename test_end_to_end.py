#!/usr/bin/env python3
"""
端到端测试 - 使用关键词兜底测试完整交互流程
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.intent import _keyword_fallback
from core.dispatcher import Dispatcher
from core.perception import Perception

def test_end_to_end():
    """测试端到端流程"""
    
    # 加载配置
    import yaml
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    print("=== 端到端流程测试 ===")
    
    # 初始化组件
    dispatcher = Dispatcher(config)
    
    # 测试指令列表
    test_commands = [
        "帮我截图看看",
        "记录当前画面",
        "这是什么"
    ]
    
    for i, command in enumerate(test_commands):
        print(f"\n--- 测试 {i+1}: {command!r} ---")
        
        # 1. 使用关键词兜底解析意图
        intent = _keyword_fallback(command)
        print(f"意图解析: action={intent['action']}, screenshot={intent['needs_screenshot']}")
        
        # 2. 如果需要截图，进行截图
        if intent.get("needs_screenshot"):
            print("✓ 需要截图 - 执行视觉处理优化")
            
            # 创建Perception实例进行截图
            perception = Perception(config, lambda x: None)
            screenshot_path = perception.take_screenshot()
            
            if screenshot_path:
                print(f"✓ 截图成功: {screenshot_path}")
                
                # 构建上下文
                context = {
                    "transcript": command,
                    "timestamp": "2026-03-25T20:50:00",
                    "screenshot": screenshot_path,
                }
                
                # 合并意图参数
                context.update(intent.get("params", {}))
                
                # 3. 执行模块
                print("执行模块...")
                result = dispatcher.dispatch(intent, context)
                print(f"执行结果: status={result.get('status')}")
                
                if result.get("message"):
                    print(f"响应消息: {result['message']}")
                
                # 检查文件大小优化效果
                from pathlib import Path
                screenshot_file = Path(screenshot_path)
                if screenshot_file.exists():
                    file_size_kb = screenshot_file.stat().st_size / 1024
                    print(f"✓ 优化后文件大小: {file_size_kb:.1f} KB")
                    
                    # 检查是否为JPEG格式
                    if screenshot_path.lower().endswith('.jpg') or screenshot_path.lower().endswith('.jpeg'):
                        print("✓ 格式: JPEG (视觉处理优化生效)")
                    else:
                        print("⚠ 格式: PNG (降级模式)")
            else:
                print("✗ 截图失败")
        else:
            print("⚠ 不需要截图")
    
    print("\n=== 端到端测试完成 ===")

if __name__ == "__main__":
    test_end_to_end()