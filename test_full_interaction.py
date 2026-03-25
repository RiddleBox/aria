#!/usr/bin/env python3
"""
完整交互测试脚本 - 测试语音+视觉端到端流程
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# 导入必要的模块
from core.intent import parse_intent
from core.dispatcher import Dispatcher
from modules.identity.persona import Persona
from core.perception import Perception

def test_interaction():
    """测试完整的交互流程"""
    
    # 加载配置
    import yaml
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    print("=== 完整交互流程测试 ===")
    
    # 初始化组件
    dispatcher = Dispatcher(config)
    persona = Persona(config)
    
    # 测试指令列表
    test_commands = [
        "帮我截图看看",
        "截个图",
        "看看屏幕内容",
        "记录当前画面"
    ]
    
    for i, command in enumerate(test_commands):
        print(f"\n--- 测试 {i+1}: {command!r} ---")
        
        # 1. 解析意图
        system_prompt = persona.get_system_prompt()
        intent = parse_intent(command, config, system_prompt)
        
        print(f"解析结果: {intent}")
        
        # 2. 检查是否需要截图
        if intent.get("needs_screenshot"):
            print("✓ 需要截图 - 测试视觉处理优化")
            
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
                result = dispatcher.dispatch(intent, context)
                print(f"执行结果: {result}")
                
                # 检查文件大小优化效果
                from pathlib import Path
                screenshot_file = Path(screenshot_path)
                if screenshot_file.exists():
                    file_size_kb = screenshot_file.stat().st_size / 1024
                    print(f"✓ 优化后文件大小: {file_size_kb:.1f} KB")
            else:
                print("✗ 截图失败")
        else:
            print("⚠ 不需要截图")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_interaction()