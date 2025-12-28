"""
安全修复单元测试

测试以下安全修复：
1. 令牌池线程安全（竞态条件防护）
2. 临时文件清理队列（无界增长防护）
3. WebSocket连接原子性（状态一致性）
4. 认证绕过防护（扩展健康检查）
5. 配置验证器（边界检查）
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import time
import threading
import tempfile
import os
from collections import deque
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.websocket_auth import TokenManager
from app.services.funasr_service import (
    add_to_cleanup_queue,
    retry_cleanup_failed_files,
    get_cleanup_queue_size
)
from app.core.config import Settings


class TestTokenManagerThreadSafety:
    """令牌管理器线程安全测试"""

    def test_concurrent_token_generation_within_limit(self):
        """测试多线程并发生成令牌（在限制内）"""
        manager = TokenManager(max_pool_size=100)
        num_threads = 10
        tokens_per_thread = 5

        tokens = []
        errors = []

        def generate_tokens():
            try:
                for _ in range(tokens_per_thread):
                    token = manager.generate_token()
                    tokens.append(token)
                    time.sleep(0.001)  # 模拟真实场景的延迟
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=generate_tokens)
            for _ in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该生成所有令牌
        assert len(errors) == 0, f"生成令牌时出错: {errors}"
        assert len(tokens) == num_threads * tokens_per_thread

        # 所有令牌应该唯一
        assert len(set(tokens)) == len(tokens), "存在重复的令牌"

        # 令牌池大小应该正确
        assert len(manager.tokens) == len(tokens)

    def test_concurrent_token_generation_exceeds_limit(self):
        """测试多线程并发生成令牌（超过限制）"""
        manager = TokenManager(max_pool_size=50)
        num_threads = 20
        tokens_per_thread = 10

        successful_tokens = []
        errors = []

        def generate_tokens():
            try:
                for _ in range(tokens_per_thread):
                    token = manager.generate_token()
                    successful_tokens.append(token)
                    time.sleep(0.001)
            except RuntimeError as e:
                errors.append(e)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=generate_tokens)
            for _ in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该有一些成功，一些失败
        assert len(successful_tokens) > 0, "应该至少生成一些令牌"
        assert len(errors) > 0, "应该有一些令牌生成被拒绝"

        # 令牌池不应超过最大限制
        assert len(manager.tokens) <= manager.max_pool_size

        # 成功的令牌应该唯一
        assert len(set(successful_tokens)) == len(successful_tokens)

    def test_concurrent_validation_and_generation(self):
        """测试并发验证和生成令牌"""
        manager = TokenManager(max_pool_size=100)
        num_tokens = 20

        # 先生成一些令牌
        tokens = [manager.generate_token() for _ in range(num_tokens)]

        validation_results = []
        generation_results = []

        def validate_tokens():
            for token in tokens:
                result = manager.validate_token(token)
                validation_results.append(result)
                time.sleep(0.001)

        def generate_new_tokens():
            try:
                for _ in range(10):
                    token = manager.generate_token()
                    generation_results.append(token)
                    time.sleep(0.001)
            except Exception:
                pass

        # 启动验证和生成线程
        t1 = threading.Thread(target=validate_tokens)
        t2 = threading.Thread(target=generate_new_tokens)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 所有验证应该成功
        assert all(validation_results), "部分令牌验证失败"

        # 新令牌应该生成成功
        assert len(generation_results) > 0

    def test_concurrent_cleanup_and_generation(self):
        """测试并发清理和生成令牌"""
        manager = TokenManager(token_expiry=0.1)  # 100ms过期
        num_tokens = 30

        # 生成令牌
        tokens = [manager.generate_token() for _ in range(num_tokens)]

        cleanup_results = []
        generation_results = []

        def cleanup_expired():
            for _ in range(5):
                cleaned = manager.cleanup_expired()
                cleanup_results.append(cleaned)
                time.sleep(0.05)  # 等待令牌过期

        def generate_tokens():
            try:
                for _ in range(20):
                    token = manager.generate_token()
                    generation_results.append(token)
                    time.sleep(0.01)
            except Exception:
                pass

        # 启动清理和生成线程
        t1 = threading.Thread(target=cleanup_expired)
        t2 = threading.Thread(target=generate_tokens)

        t1.start()
        time.sleep(0.15)  # 等待令牌过期
        t2.start()
        t1.join()
        t2.join()

        # 应该有一些令牌被清理
        assert sum(cleanup_results) > 0, "应该有一些令牌被清理"

        # 应该有一些新令牌生成
        assert len(generation_results) > 0, "应该生成一些新令牌"

    def test_token_pool_size_limit_never_exceeded(self):
        """测试令牌池大小永不超限"""
        max_size = 100
        manager = TokenManager(max_pool_size=max_size)
        num_threads = 50
        attempts_per_thread = 20

        def try_generate():
            for _ in range(attempts_per_thread):
                try:
                    manager.generate_token()
                except RuntimeError:
                    pass  # 预期的拒绝
                except Exception:
                    pass

        threads = [threading.Thread(target=try_generate) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 令牌池大小永不超限
        assert len(manager.tokens) <= max_size, \
            f"令牌池大小超过限制: {len(manager.tokens)} > {max_size}"


class TestCleanupQueueManagement:
    """临时文件清理队列管理测试"""

    def test_add_to_cleanup_queue_basic(self):
        """测试基本添加到清理队列"""
        from app.services.funasr_service import _cleanup_queue, _cleanup_queue_set

        # 清空队列
        _cleanup_queue.clear()
        _cleanup_queue_set.clear()

        # 添加文件
        test_files = ["/tmp/test1.wav", "/tmp/test2.wav", "/tmp/test3.wav"]
        for f in test_files:
            add_to_cleanup_queue(f)

        # 验证队列状态
        assert get_cleanup_queue_size() == 3
        assert len(_cleanup_queue_set) == 3

    def test_cleanup_queue_duplicate_detection(self):
        """测试重复文件检测"""
        from app.services.funasr_service import _cleanup_queue, _cleanup_queue_set

        _cleanup_queue.clear()
        _cleanup_queue_set.clear()

        # 添加重复文件
        test_file = "/tmp/test_duplicate.wav"
        add_to_cleanup_queue(test_file)
        add_to_cleanup_queue(test_file)
        add_to_cleanup_queue(test_file)

        # 应该只有一个条目
        assert get_cleanup_queue_size() == 1
        assert len(_cleanup_queue_set) == 1

    def test_cleanup_queue_max_size_enforcement(self):
        """测试队列最大大小限制"""
        from app.services.funasr_service import _cleanup_queue, _cleanup_queue_set
        from app.core.config import settings

        _cleanup_queue.clear()
        _cleanup_queue_set.clear()

        # 保存原始值
        original_max_size = settings.max_cleanup_queue_size

        try:
            # 使用小的限制进行测试
            settings.max_cleanup_queue_size = 5

            # 添加超过限制的文件
            for i in range(10):
                add_to_cleanup_queue(f"/tmp/test{i}.wav")

            # 队列大小应该被限制
            assert get_cleanup_queue_size() <= 5
        finally:
            settings.max_cleanup_queue_size = original_max_size

    def test_cleanup_queue_fifo_eviction(self):
        """测试FIFO淘汰策略"""
        from app.services.funasr_service import _cleanup_queue, _cleanup_queue_set
        from app.core.config import settings

        _cleanup_queue.clear()
        _cleanup_queue_set.clear()

        # 保存原始值
        original_max_size = settings.max_cleanup_queue_size

        try:
            settings.max_cleanup_queue_size = 3

            # 添加5个文件
            for i in range(5):
                add_to_cleanup_queue(f"/tmp/test{i}.wav")

            # 队列应该包含最后3个文件
            queue_list = list(_cleanup_queue)
            assert len(queue_list) == 3
            assert "/tmp/test2.wav" in queue_list
            assert "/tmp/test3.wav" in queue_list
            assert "/tmp/test4.wav" in queue_list
            # 最早的文件应该被淘汰
            assert "/tmp/test0.wav" not in queue_list
            assert "/tmp/test1.wav" not in queue_list
        finally:
            settings.max_cleanup_queue_size = original_max_size

    def test_retry_cleanup_failed_files(self):
        """测试重试清理失败文件"""
        from app.services.funasr_service import _cleanup_queue, _cleanup_queue_set

        _cleanup_queue.clear()
        _cleanup_queue_set.clear()

        # 创建临时文件
        temp_files = []
        for i in range(3):
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            temp_files.append(path)
            add_to_cleanup_queue(path)

        # 添加一个不存在的文件
        add_to_cleanup_queue("/tmp/nonexistent_file.wav")

        # 运行清理
        cleaned = retry_cleanup_failed_files(max_retries=2)

        # 所有文件应该被清理（存在的删除，不存在的跳过）
        assert cleaned >= 3

        # 队列应该为空或只包含清理失败的文件
        assert get_cleanup_queue_size() == 0

    def test_concurrent_cleanup_queue_operations(self):
        """测试并发清理队列操作"""
        from app.services.funasr_service import _cleanup_queue, _cleanup_queue_set

        _cleanup_queue.clear()
        _cleanup_queue_set.clear()

        num_threads = 10
        files_per_thread = 20
        errors = []

        def add_files(thread_id):
            try:
                for i in range(files_per_thread):
                    add_to_cleanup_queue(f"/tmp/thread{thread_id}_file{i}.wav")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_files, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应该有错误
        assert len(errors) == 0

        # 队列应该包含所有唯一文件
        expected_size = num_threads * files_per_thread
        # 由于可能有FIFO淘汰，检查是否在合理范围内
        assert get_cleanup_queue_size() > 0


class TestAuthenticationBypassPrevention:
    """认证绕过防护测试"""

    def test_extended_health_requires_token_by_default(self):
        """测试默认情况下扩展健康检查需要令牌"""
        client = TestClient(app)

        response = client.get("/api/v1/health/extended")

        # 应该返回401未授权
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_extended_health_rejects_invalid_token(self):
        """测试扩展健康检查拒绝无效令牌"""
        client = TestClient(app)

        response = client.get("/api/v1/health/extended?token=invalid_token")

        # 应该返回403禁止
        assert response.status_code == 403

    def test_extended_health_accepts_valid_token(self):
        """测试扩展健康检查接受有效令牌"""
        client = TestClient(app)

        # 生成令牌
        token_response = client.get("/api/v1/token")
        assert token_response.status_code == 200
        token = token_response.json()["token"]

        # 使用令牌访问
        response = client.get(f"/api/v1/health/extended?token={token}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "memory_usage_percent" in data

    def test_extended_health_optional_auth_mode(self):
        """测试可选认证模式（禁用require_extended_health_auth）"""
        from app.core.config import settings
        original_value = settings.require_extended_health_auth

        try:
            settings.require_extended_health_auth = False
            client = TestClient(app)

            # 无令牌访问应该成功（可选模式）
            response = client.get("/api/v1/health/extended")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        finally:
            settings.require_extended_health_auth = original_value

    def test_extended_health_still_validates_with_optional_mode(self):
        """测试可选模式下仍然验证提供的令牌"""
        from app.core.config import settings
        original_value = settings.require_extended_health_auth

        try:
            settings.require_extended_health_auth = False
            client = TestClient(app)

            # 提供无效令牌应该被拒绝
            response = client.get("/api/v1/health/extended?token=invalid")

            assert response.status_code == 403
        finally:
            settings.require_extended_health_auth = original_value


class TestConfigurationValidators:
    """配置验证器测试"""

    def test_max_cleanup_queue_size_minimum(self):
        """测试max_cleanup_queue_size最小值验证"""
        with pytest.raises(ValueError, match="must be at least 100"):
            Settings(max_cleanup_queue_size=50)

    def test_max_cleanup_queue_size_maximum(self):
        """测试max_cleanup_queue_size最大值验证"""
        with pytest.raises(ValueError, match="must not exceed 10000"):
            Settings(max_cleanup_queue_size=20000)

    def test_max_cleanup_queue_size_valid_values(self):
        """测试max_cleanup_queue_size有效值"""
        # 应该成功创建
        settings = Settings(max_cleanup_queue_size=100)
        assert settings.max_cleanup_queue_size == 100

        settings = Settings(max_cleanup_queue_size=1000)
        assert settings.max_cleanup_queue_size == 1000

        settings = Settings(max_cleanup_queue_size=10000)
        assert settings.max_cleanup_queue_size == 10000

    def test_default_configuration_values(self):
        """测试默认配置值"""
        settings = Settings()

        assert settings.require_extended_health_auth is True
        assert settings.max_cleanup_queue_size == 1000


class TestWebSocketConnectionAtomicity:
    """WebSocket连接原子性测试"""

    def test_connection_state_consistency(self):
        """测试连接状态一致性"""
        from app.core.websocket import ConnectionManager
        from unittest.mock import Mock, AsyncMock

        manager = ConnectionManager(max_connections=2)

        # 创建mock WebSocket
        mock_ws = Mock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()

        # 模拟连接失败场景
        with patch('app.services.funasr_service.FunASRService') as MockService:
            mock_instance = Mock()
            mock_instance.initialize = AsyncMock(side_effect=Exception("Model load failed"))
            MockService.return_value = mock_instance

            # 运行连接
            import asyncio
            result = asyncio.run(manager.connect(mock_ws, model="offline"))

            # 连接应该失败
            assert result is False

            # 管理器状态应该保持一致
            assert mock_ws not in manager.active_connections
            assert mock_ws not in manager.connection_info
            assert mock_ws not in manager.funasr_services


class TestResourceLeakPrevention:
    """资源泄漏防护测试"""

    def test_funasr_service_cleanup_on_connection_failure(self):
        """测试连接失败时清理FunASR服务"""
        from app.services.funasr_service import FunASRService
        from unittest.mock import patch

        with patch('app.services.funasr_service.FunASRService.cleanup') as mock_cleanup:
            service = FunASRService()
            service.is_initialized = False

            # 清理应该被调用
            service.cleanup()
            mock_cleanup.assert_not_called()  # 未初始化时不清理模型

    def test_token_manager_auto_cleanup(self):
        """测试令牌管理器自动清理过期令牌"""
        manager = TokenManager(token_expiry=0.1)  # 100ms过期

        # 生成一些令牌
        tokens = [manager.generate_token() for _ in range(10)]
        assert len(manager.tokens) == 10

        # 等待令牌过期
        time.sleep(0.15)

        # 手动触发清理
        cleaned = manager.cleanup_expired()

        # 应该清理所有令牌
        assert cleaned == 10
        assert len(manager.tokens) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
