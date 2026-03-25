#!/usr/bin/env python3
"""
截图功能测试脚本 - 直接测试视觉处理优化
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.perception import Perception

def test_screenshot_optimization():
    """测试截图优化功能"""
    
    # 加载配置
    import yaml
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 创建Perception实例
    perception = Perception(config, lambda x: None)
    
    print("=== 视觉处理优化测试 ===")
    print("测试参数:")
    print(f"  最大宽度: {config['perception']['screenshot']['max_width']}")
    print(f"  最大高度: {config['perception']['screenshot']['max_height']}")
    print(f"  JPEG质量: {config['perception']['screenshot']['jpeg_quality']}")
    print()
    
    # 测试截图功能
    print("正在截图...")
    try:
        screenshot_path = perception.take_screenshot()
        
        if screenshot_path:
            print(f"✓ 截图成功: {screenshot_path}")
            
            # 检查文件信息
            from pathlib import Path
            screenshot_file = Path(screenshot_path)
            if screenshot_file.exists():
                file_size_kb = screenshot_file.stat().st_size / 1024
                print(f"✓ 文件大小: {file_size_kb:.1f} KB")
                
                # 检查是否为JPEG格式
                if screenshot_path.lower().endswith('.jpg') or screenshot_path.lower().endswith('.jpeg'):
                    print("✓ 格式: JPEG (优化生效)")
                else:
                    print("⚠ 格式: PNG (降级模式)")
            else:
                print("✗ 文件不存在")
        else:
            print("✗ 截图失败")
    except Exception as e:
        print(f"✗ 截图过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_screenshot_optimization()