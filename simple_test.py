#!/usr/bin/env python3
"""
简单截图测试 - 验证基础功能
"""

import mss
import mss.tools
from pathlib import Path
from datetime import datetime

def simple_screenshot_test():
    """简单截图测试"""
    print("=== 简单截图测试 ===")
    
    try:
        # 创建输出目录
        out_dir = Path("data") / "captures"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用mss截图
        with mss.mss() as sct:
            # 获取主显示器
            monitor = sct.monitors[1]
            print(f"主显示器信息: {monitor}")
            
            # 截图
            print("正在截图...")
            img = sct.grab(monitor)
            print(f"截图尺寸: {img.width}x{img.height}")
            
            # 保存为PNG
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            png_path = out_dir / f"test_simple_{ts}.png"
            mss.tools.to_png(img.rgb, img.size, output=str(png_path))
            
            if png_path.exists():
                file_size_kb = png_path.stat().st_size / 1024
                print(f"✓ PNG截图成功: {png_path.name}")
                print(f"✓ 文件大小: {file_size_kb:.1f} KB")
            else:
                print("✗ PNG保存失败")
                
    except Exception as e:
        print(f"✗ 截图错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_screenshot_test()