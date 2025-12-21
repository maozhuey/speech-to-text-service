#!/usr/bin/env python3
"""
前端样式验证脚本
检查CSS文件是否存在且完整
"""
import os
import sys
from pathlib import Path

def check_css_files():
    """检查CSS文件是否完整"""
    frontend_dir = Path("frontend")
    css_file = frontend_dir / "css" / "styles.css"
    index_file = frontend_dir / "index.html"

    issues = []

    # 检查CSS文件是否存在
    if not css_file.exists():
        issues.append("❌ CSS文件不存在: frontend/css/styles.css")
    else:
        # 检查CSS文件大小
        size = css_file.stat().st_size
        if size < 1000:  # 小于1KB可能有问题
            issues.append(f"⚠️ CSS文件过小: {size} bytes")
        else:
            print(f"✅ CSS文件存在: {size} bytes")

    # 检查HTML中的CSS引用
    if index_file.exists():
        content = index_file.read_text(encoding='utf-8')
        if 'href="css/styles.css"' in content:
            print("✅ HTML正确引用CSS文件")
        else:
            issues.append("❌ HTML文件未正确引用CSS文件")
    else:
        issues.append("❌ index.html文件不存在")

    return issues

def check_tailwind_dependency():
    """检查是否还依赖Tailwind CDN"""
    index_file = Path("frontend/index.html")
    if index_file.exists():
        content = index_file.read_text(encoding='utf-8')
        if 'tailwindcss' in content.lower():
            return True
    return False

if __name__ == "__main__":
    print("=== 前端样式检查 ===\n")

    # 检查CSS文件
    issues = check_css_files()

    # 检查Tailwind依赖
    if check_tailwind_dependency():
        print("⚠️ 仍然依赖Tailwind CDN")
    else:
        print("✅ 已移除Tailwind CDN依赖")

    # 输出结果
    if issues:
        print("\n发现问题:")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("\n✅ 所有检查通过！")

        # 验证样式类是否存在
        css_file = Path("frontend/css/styles.css")
        if css_file.exists():
            css_content = css_file.read_text(encoding='utf-8')
            essential_classes = ['.bg-gray-800', '.text-white', '.flex', '.container']
            missing_classes = [cls for cls in essential_classes if cls not in css_content]

            if missing_classes:
                print(f"\n⚠️ CSS文件可能缺少以下类: {missing_classes}")
            else:
                print("✅ CSS文件包含必要的样式类")