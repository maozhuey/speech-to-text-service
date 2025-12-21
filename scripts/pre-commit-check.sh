#!/bin/bash
# 提交前检查脚本
# 确保所有关键文件都存在且正确

echo "=== 提交前检查 ==="

# 检查样式文件
if [ ! -f "frontend/css/styles.css" ]; then
    echo "❌ 错误: 缺少CSS文件"
    exit 1
fi

# 检查CSS文件大小
CSS_SIZE=$(stat -f%z frontend/css/styles.css 2>/dev/null || stat -c%s frontend/css/styles.css 2>/dev/null)
if [ "$CSS_SIZE" -lt 1000 ]; then
    echo "❌ 错误: CSS文件过小，可能不完整"
    exit 1
fi

# 检查HTML文件中的引用
if ! grep -q 'href="css/styles.css"' frontend/index.html; then
    echo "❌ 错误: HTML文件未正确引用CSS"
    exit 1
fi

# 检查是否意外依赖CDN
if grep -qi tailwind frontend/index.html; then
    echo "⚠️ 警告: 仍然依赖Tailwind CDN"
fi

echo "✅ 所有检查通过！"
echo "💡 提示: 提交前请在浏览器中验证样式是否正常"