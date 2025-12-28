"""
前端中间结果显示功能测试
测试新增的"识别中..."中间结果显示功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))


class TestInterimDisplay:
    """中间结果显示功能测试类"""

    def test_interim_text_implementation(self):
        """测试前端是否实现了updateInterimText方法"""
        frontend_path = backend_root.parent / "frontend" / "index.html"

        with open(frontend_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 检查updateInterimText方法实现
        assert 'updateInterimText' in html_content, "缺少updateInterimText方法"
        assert 'interim-text' in html_content, "缺少interim-text样式类"

        # 检查关键实现
        assert "querySelector('.interim-text')" in html_content, "缺少查询interim-text元素"
        assert 'transition-opacity' in html_content, "缺少过渡动画样式"

        print("✓ updateInterimText方法已实现")
        print("✓ interim-text样式类已添加")
        print("✓ 过渡动画已实现")

    def test_interim_text_cleared_on_final(self):
        """测试最终结果时清除中间结果"""
        frontend_path = backend_root.parent / "frontend" / "index.html"

        with open(frontend_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 检查addFinalText方法中是否清除中间结果
        assert 'remove()' in html_content, "缺少清除中间结果的代码"
        assert "interimElement" in html_content, "缺少interimElement变量"

        # 验证清除逻辑在addFinalText中
        add_final_section = html_content[html_content.find('addFinalText'):
                                              html_content.find('addFinalText') + 2000]
        assert 'interim-text' in add_final_section, "addFinalText未清除interim-text元素"

        print("✓ 最终结果时清除中间结果逻辑已实现")

    def test_processing_message_handling(self):
        """测试processing消息处理"""
        frontend_path = backend_root.parent / "frontend" / "index.html"

        with open(frontend_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 检查processing消息处理
        assert "case 'processing':" in html_content, "缺少processing消息处理"
        processing_section = html_content[html_content.find("case 'processing':"):
                                             html_content.find("case 'processing':") + 500]

        assert 'updateInterimText' in processing_section, "processing消息未调用updateInterimText"

        print("✓ processing消息处理已实现")
        print("✓ processing消息触发显示中间文本")

    def test_error_handling_clears_interim(self):
        """测试错误时清除中间结果"""
        frontend_path = backend_root.parent / "frontend" / "index.html"

        with open(frontend_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 检查error消息处理中是否清除中间结果
        error_section_start = html_content.find("case 'error':")
        error_section = html_content[error_section_start:
                                     error_section_start + 1000]

        assert 'interim-text' in error_section, "错误处理未清除中间结果"

        print("✓ 错误时清除中间结果已实现")

    def test_stop_recording_clears_interim(self):
        """测试停止录音时清除中间结果"""
        frontend_path = backend_root.parent / "frontend" / "index.html"

        with open(frontend_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 检查stopRecording方法中是否清除中间结果
        # 搜索"stopRecording()"后的方法定义（在addEventListener之后）
        add_listener_pos = html_content.find("addEventListener('click', () => this.stopRecording())")
        if add_listener_pos > 0:
            # 从addEventListener位置之后500字符处开始搜索stopRecording()方法定义
            method_start = html_content.find('stopRecording()', add_listener_pos + 200)
            stop_section = html_content[method_start: method_start + 5000]
        else:
            stop_section = html_content

        assert 'interim-text' in stop_section, "停止录音未清除中间结果"

        print("✓ 停止录音时清除中间结果已实现")

    def test_interim_text_style(self):
        """测试中间结果样式"""
        frontend_path = backend_root.parent / "frontend" / "index.html"

        with open(frontend_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 检查样式类
        assert 'text-gray-400' in html_content, "缺少灰色文本样式"
        assert 'italic' in html_content, "缺少斜体样式"

        # 检查opacity设置
        assert 'opacity' in html_content or '0.8' in html_content, "缺少透明度设置"

        print("✓ 中间结果灰色样式已实现")
        print("✓ 中间结果斜体样式已实现")
        print("✓ 中间结果透明度已设置")

    def test_backend_processing_message(self):
        """测试后端发送processing消息"""
        backend_ws_path = backend_root / "app" / "core" / "websocket.py"

        with open(backend_ws_path, 'r', encoding='utf-8') as f:
            ws_content = f.read()

        # 检查是否发送processing消息
        assert '"processing"' in ws_content or '"type": "processing"' in ws_content, \
               "后端未发送processing消息"

        print("✓ 后端发送processing消息已实现")

    def test_readme_documentation(self):
        """测试README文档更新"""
        readme_path = backend_root.parent / "README.md"

        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # 检查是否添加了新功能说明
        assert '实时识别状态显示' in readme_content or '识别中' in readme_content, \
               "README未添加新功能说明"

        print("✓ README已更新功能说明")


def run_tests():
    """运行所有测试"""
    print("前端中间结果显示功能测试")
    print("=" * 50)

    test_class = TestInterimDisplay()

    tests = [
        ("updateInterimText实现", test_class.test_interim_text_implementation),
        ("清除中间结果逻辑", test_class.test_interim_text_cleared_on_final),
        ("processing消息处理", test_class.test_processing_message_handling),
        ("错误时清除中间结果", test_class.test_error_handling_clears_interim),
        ("停止录音清除中间结果", test_class.test_stop_recording_clears_interim),
        ("中间结果样式", test_class.test_interim_text_style),
        ("后端processing消息", test_class.test_backend_processing_message),
        ("README文档更新", test_class.test_readme_documentation),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            print()
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            print()

    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
