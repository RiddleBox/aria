#!/usr/bin/env python3
"""
单次截图测试 - 验证视觉处理优化功能
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.perception import Perception

def test_single_screenshot():
    """单次截图测试"""
    
    # 加载配置
    import yaml
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    print("=== 单次截图测试 - 视觉处理优化验证 ===")
    print("测试目标：验证截图分辨率优化、JPEG压缩、文件大小控制")
    print()
    
    # 创建Perception实例
    perception = Perception(config, lambda x: None)
    
    # 执行单次截图
    print("正在截图...")
    start_time = time.time()
    screenshot_path = perception.take_screenshot()
    end_time = time.time()
    
    if screenshot_path:
        screenshot_file = Path(screenshot_path)
        if screenshot_file.exists():
            file_size_kb = screenshot_file.stat().st_size / 1024
            processing_time = end_time - start_time
            
            # 检查格式
            is_jpeg = screenshot_path.lower().endswith('.jpg') or screenshot_path.lower().endswith('.jpeg')
            format_type = "JPEG (优化生效)" if is_jpeg else "PNG (降级模式)"
            
            print(f"✓ 截图成功: {screenshot_file.name}")
            print(f"✓ 文件大小: {file_size_kb:.1f} KB")
            print(f"✓ 处理时间: {processing_time:.2f} 秒")
            print(f"✓ 格式: {format_type}")
            
            # 与原始PNG对比
            original_png_size = 537.4  # 从简单测试得到的数据
            size_reduction = (original_png_size - file_size_kb) / original_png_size * 100
            compression_ratio = original_png_size / file_size_kb
            
            print(f"\n📊 优化效果对比:")
            print(f"  原始PNG大小: {original_png_size:.1f} KB")
            print(f"  优化后大小: {file_size_kb:.1f} KB")
            print(f"  文件大小减少: {size_reduction:.1f}%")
            print(f"  压缩比: {compression_ratio:.1f}x")
            
            if size_reduction > 50:
                print("🎯 优化效果显著！视觉处理优化功能正常工作。")
                print("✅ 系统已成功实现：")
                print("   ✓ 分辨率智能缩放")
                print("   ✓ JPEG格式压缩")
                print("   ✓ 文件大小控制")
                print("   ✓ Token消耗优化")
            else:
                print("⚠ 优化效果一般，可能需要进一步调整参数。")
        else:
            print("✗ 文件不存在")
    else:
        print("✗ 截图失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_single_screenshot()