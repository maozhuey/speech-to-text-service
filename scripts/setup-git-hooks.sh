#!/bin/bash
# 设置Git Hooks，在提交前自动检查

echo "设置Git Hooks..."

# 创建pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Git pre-commit hook

echo "🔍 运行提交前检查..."

# 运行样式检查
python scripts/validate_styles.py
if [ $? -ne 0 ]; then
    echo "❌ 样式检查失败，提交被中止"
    echo "请修复上述问题后再提交"
    exit 1
fi

# 检查是否有大文件被意外添加
if git diff --cached --name-only | xargs ls -la 2>/dev/null | awk '$5 > 1048576 {print $9, $5, "bytes (>1MB)"}'; then
    echo "⚠️ 警告: 检测到大文件，请确认是否需要提交"
fi

echo "✅ 提交前检查通过"
EOF

chmod +x .git/hooks/pre-commit

echo "✅ Git Hooks设置完成！"
echo "现在每次提交前都会自动检查样式文件"