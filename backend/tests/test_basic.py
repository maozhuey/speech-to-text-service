"""
基础功能测试
"""

import sys
import os
from pathlib import Path

# 添加项目根目录和后端目录到Python路径
project_root = Path(__file__).parent.parent
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(project_root))

def test_imports():
    """测试主要模块是否可以正常导入"""
    from app.core.config import settings
    from app.core.websocket import ConnectionManager
    # 导入成功则测试通过
    assert settings is not None
    assert ConnectionManager is not None

def test_config():
    """测试配置加载"""
    from app.core.config import settings

    # 验证配置值
    assert settings.max_connections > 0
    assert settings.sample_rate > 0
    assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]

    # 验证新的CORS配置
    assert hasattr(settings, 'get_allowed_origins_list')
    origins = settings.get_allowed_origins_list()
    assert isinstance(origins, list)

def test_websocket_manager():
    """测试WebSocket连接管理器"""
    from app.core.websocket import ConnectionManager

    manager = ConnectionManager(max_connections=2)

    assert manager.max_connections == 2
    assert manager.get_connection_count() == 0
    assert manager.is_connection_available() is True

def main():
    """运行所有测试"""
    print("语音转文本服务 - 基础功能测试")
    print("=" * 40)

    tests = [
        test_imports,
        test_config,
        test_websocket_manager
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("✓ 所有基础功能测试通过！")
        return True
    else:
        print("✗ 部分测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)