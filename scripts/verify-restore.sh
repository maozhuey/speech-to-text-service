#!/bin/bash
# Git恢复后验证脚本
# 确保恢复后所有功能正常

echo "=== Git恢复后验证 ==="

# 1. 检查前端文件完整性
echo "1. 检查前端文件..."
if [ -f "frontend/css/styles.css" ] && [ -f "frontend/index.html" ]; then
    echo "   ✅ 前端文件存在"
else
    echo "   ❌ 前端文件缺失"
    exit 1
fi

# 2. 验证样式
echo "2. 验证样式文件..."
python scripts/validate_styles.py

# 3. 检查端口占用
echo "3. 检查服务端口..."
if lsof -i :8002 > /dev/null 2>&1; then
    echo "   ✅ 后端端口8002已使用"
else
    echo "   ⚠️ 后端端口8002空闲，需要启动服务"
fi

if lsof -i :8081 > /dev/null 2>&1 || lsof -i :8080 > /dev/null 2>&1; then
    echo "   ✅ 前端端口已使用"
else
    echo "   ⚠️ 前端端口空闲，需要启动服务"
fi

# 4. 给出清理缓存的提示
echo ""
echo "=== 重要提示 ==="
echo "如果样式显示不正常，请："
echo "1. 强制刷新浏览器 (Cmd+Shift+R)"
echo "2. 或使用无痕模式访问"
echo "3. 或清除浏览器缓存"
echo ""
echo "访问地址："
echo "- 前端: http://localhost:8081 或 http://localhost:8080"
echo "- 后端: http://localhost:8002"