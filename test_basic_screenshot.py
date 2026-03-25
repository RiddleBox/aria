#!/usr/bin/env python3
"""
基础截图测试 - 验证MSS库基本功能
"""

import sys
import time
from pathlib import Path
from datetime import datetime

def test_basic_screenshot():
    """基础截图测试"""
    
    print("=== 基础截图测试 ===")
    print("测试目标：验证MSS库基本功能，不使用OpenCV复杂处理")
    print()
    
    try:
        import mss
        import mss.tools
        
        # 创建输出目录
        out_dir = Path(__file__).parent / "data" / "captures"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print("1. 测试MSS库导入和初始化...")
        with mss.mss() as sct:
            print("✓ MSS库初始化成功")
            
            # 获取显示器信息
            monitors = sct.monitors
            print(f"✓ 检测到 {len(monitors)} 个显示器")
            for i, monitor in enumerate(monitors):
                print(f"   显示器 {i}: {monitor}")
            
            # 使用主显示器
            monitor = monitors[1]
            print(f"✓ 使用主显示器: {monitor}")
            
            print("2. 执行截图...")
            start_time = time.time()
            img = sct.grab(monitor)
            end_time = time.time()
            
            print(f"✓ 截图成功: {img.width}x{img.height}")
            print(f"✓ 截图时间: {end_time - start_time:.2f} 秒")
            
            # 保存为PNG
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            png_path = out_dir / f"basic_test_{ts}.png"
            mss.tools.to_png(img.rgb, img.size, output=str(png_path))
            
            if png_path.exists():
                file_size_kb = png_path.stat().st_size / 1024
                print(f"✓ PNG保存成功: {png_path.name}")
                print(f"✓ 文件大小: {file_size_kb:.1f} KB")
                
                # 测试OpenCV基本功能
                print("\n3. 测试OpenCV基本功能...")
                try:
                    import cv2
                    import numpy as np
                    
                    # 读取PNG文件
                    img_cv = cv2.imread(str(png_path))
                    if img_cv is not None:
                        print("✓ OpenCV读取图像成功")
                        print(f"✓ 图像尺寸: {img_cv.shape[1]}x{img_cv.shape[0]}")
                        
                        # 测试简单的缩放
                        scale = 0.5
                        new_width = int(img_cv.shape[1] * scale)
                        new_height = int(img_cv.shape[0] * scale)
                        resized = cv2.resize(img_cv, (new_width, new_height))
                        print(f"✓ 缩放测试: {img_cv.shape[1]}x{img_cv.shape[0]} -> {new_width}x{new_height}")
                        
                        # 测试JPEG保存
                        jpeg_path = out_dir / f"basic_test_{ts}.jpg"
                        cv2.imwrite(str(jpeg_path), resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        
                        if jpeg_path.exists():
                            jpeg_size_kb = jpeg_path.stat().st_size / 1024
                            print(f"✓ JPEG保存成功: {jpeg_path.name}")
                            print(f"✓ JPEG大小: {jpeg_size_kb:.1f} KB")
                            
                            # 对比压缩效果
                            compression_ratio = file_size_kb / jpeg_size_kb
                            print(f"✓ 压缩比: {compression_ratio:.1f}x")
                            
                            if compression_ratio > 1.5:
                                print("🎯 JPEG压缩效果显著！")
                            else:
                                print("⚠ JPEG压缩效果一般")
                        else:
                            print("✗ JPEG保存失败")
                    else:
                        print("✗ OpenCV读取图像失败")
                        
                except Exception as e:
                    print(f"✗ OpenCV测试失败: {e}")
                    
            else:
                print("✗ PNG保存失败")
                
    except Exception as e:
        print(f"✗ 基础截图测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 基础测试完成 ===")

if __name__ == "__main__":
    test_basic_screenshot()