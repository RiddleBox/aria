#!/usr/bin/env python3
"""
视觉优化功能测试 - 专注于测试截图和文件优化效果
"""

import sys
import time
import random
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.perception import Perception

def test_visual_optimization():
    """测试视觉处理优化功能"""
    
    # 加载配置
    import yaml
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    print("=== 视觉处理优化功能测试 ===")
    print("测试目标：验证截图分辨率优化、JPEG压缩、文件大小控制")
    print()
    
    # 创建Perception实例
    perception = Perception(config, lambda x: None)
    
    # 测试多次截图，验证稳定性
    test_count = 3
    results = []
    
    for i in range(test_count):
        print(f"\n--- 测试 {i+1}/{test_count} ---")
        
        # 添加延迟避免文件名冲突
        if i > 0:
            delay = random.uniform(1.0, 2.0)  # 1-2秒随机延迟
            print(f"等待 {delay:.1f} 秒避免文件名冲突...")
            time.sleep(delay)
        
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
                
                result = {
                    "path": screenshot_path,
                    "size_kb": file_size_kb,
                    "time": processing_time,
                    "format": format_type,
                    "is_jpeg": is_jpeg
                }
                results.append(result)
                
                print(f"✓ 截图成功: {screenshot_file.name}")
                print(f"✓ 文件大小: {file_size_kb:.1f} KB")
                print(f"✓ 处理时间: {processing_time:.2f} 秒")
                print(f"✓ 格式: {format_type}")
            else:
                print("✗ 文件不存在")
        else:
            print("✗ 截图失败")
    
    # 统计分析
    if results:
        print(f"\n=== 测试结果分析 ===")
        print(f"测试次数: {len(results)}")
        
        avg_size = sum(r['size_kb'] for r in results) / len(results)
        avg_time = sum(r['time'] for r in results) / len(results)
        jpeg_count = sum(1 for r in results if r['is_jpeg'])
        
        print(f"平均文件大小: {avg_size:.1f} KB")
        print(f"平均处理时间: {avg_time:.2f} 秒")
        print(f"JPEG格式成功率: {jpeg_count}/{len(results)} ({jpeg_count/len(results)*100:.0f}%)")
        
        # 与原始PNG对比
        original_png_size = 537.4  # 从简单测试得到的数据
        size_reduction = (original_png_size - avg_size) / original_png_size * 100
        print(f"\n📊 优化效果对比:")
        print(f"  原始PNG大小: {original_png_size:.1f} KB")
        print(f"  优化后大小: {avg_size:.1f} KB")
        print(f"  文件大小减少: {size_reduction:.1f}%")
        print(f"  压缩比: {original_png_size/avg_size:.1f}x")
        
        if size_reduction > 50:
            print("🎯 优化效果显著！视觉处理优化功能正常工作。")
        else:
            print("⚠ 优化效果一般，可能需要进一步调整参数。")
    
    print("\n=== 视觉优化测试完成 ===")

if __name__ == "__main__":
    test_visual_optimization()