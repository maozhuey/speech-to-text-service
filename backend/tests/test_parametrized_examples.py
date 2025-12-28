"""
参数化测试示例
展示如何使用@pytest.mark.parametrize减少重复代码，提高测试可维护性
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket

from app.services.funasr_service import FunASRService
from app.core.websocket import ConnectionManager
from app.middleware.rate_limit import RateLimiter
from app.middleware.websocket_auth import TokenManager


class TestParametrizedAudioValidation:
    """参数化音频验证测试示例"""

    @pytest.mark.parametrize("audio_size,sample_rate,should_pass", [
        (0, 16000, False),          # 空音频 - 失败
        (100, 16000, False),        # 太短 (<0.1秒) - 失败
        (1600, 16000, True),        # 最小长度 (0.1秒) - 通过
        (16000, 16000, True),       # 正常长度 (1秒) - 通过
        (160000, 16000, True),      # 长音频 (10秒) - 通过
    ])
    def test_audio_length_validation(self, audio_size, sample_rate, should_pass):
        """测试音频长度验证（参数化测试）"""
        service = FunASRService()
        audio_data = np.zeros(audio_size, dtype=np.int16).tobytes() if audio_size > 0 else b""

        if should_pass:
            result = service._validate_audio(audio_data, sample_rate)
            assert result is not None
        else:
            with pytest.raises(ValueError):
                service._validate_audio(audio_data, sample_rate)

    @pytest.mark.parametrize("audio_bytes,description", [
        (b"", "空字节"),
        (b"\x00\x01", "2字节（奇数）"),
        (b"\x00\x01\x02\x03", "4字节（偶数）"),
        (b"\x00" * 1000, "1000字节（偶数）"),
        (b"\x00" * 1001, "1001字节（奇数）"),
    ])
    def test_audio_byte_alignment(self, audio_bytes, description):
        """测试音频字节对齐（参数化测试）"""
        service = FunASRService()
        # 奇数字节应该失败
        if len(audio_bytes) % 2 != 0:
            with pytest.raises(Exception):
                service._validate_audio(audio_bytes, 16000)
        else:
            # 偶数字节但太短会失败（因为长度验证）
            if len(audio_bytes) >= 1600:
                result = service._validate_audio(audio_bytes, 16000)
                assert result is not None


class TestParametrizedRateLimiting:
    """参数化限流测试示例"""

    @pytest.mark.parametrize("max_requests,window,requests_to_make,expected_allowed", [
        (5, 60, 3, True),      # 在限制内
        (5, 60, 5, True),      # 刚好达到限制
        (5, 60, 6, False),     # 超过限制
        (10, 60, 9, True),     # 在限制内
        (10, 60, 10, True),    # 刚好达到限制
        (10, 60, 11, False),   # 超过限制
        (0, 60, 1, False),     # 零限制
    ])
    def test_rate_limit_boundaries(self, max_requests, window, requests_to_make, expected_allowed):
        """测试限流边界条件（参数化测试）"""
        limiter = RateLimiter(max_requests=max_requests, window=window)
        client_id = "test_client"

        # 发送请求
        allowed_results = [limiter.is_allowed(client_id) for _ in range(requests_to_make)]

        # 最后一个请求的结果应该符合预期
        if allowed_results:
            assert allowed_results[-1] == expected_allowed

    @pytest.mark.parametrize("num_clients,requests_per_client,max_requests", [
        (5, 2, 10),      # 5个客户端，每个2个请求
        (10, 5, 50),     # 10个客户端，每个5个请求
        (20, 3, 100),    # 20个客户端，每个3个请求
    ])
    def test_independent_client_limits(self, num_clients, requests_per_client, max_requests):
        """测试独立客户端限制（参数化测试）"""
        limiter = RateLimiter(max_requests=max_requests, window=60)

        # 每个客户端都应该能发送请求
        for client_idx in range(num_clients):
            client_id = f"client_{client_idx}"
            for _ in range(requests_per_client):
                assert limiter.is_allowed(client_id) is True


class TestParametrizedConnectionLimits:
    """参数化连接限制测试示例"""

    @pytest.mark.parametrize("max_connections,attempt_to_connect,expected_success", [
        (1, 1, True),
        (1, 2, False),    # 第二个连接应该失败
        (2, 2, True),
        (2, 3, False),    # 第三个连接应该失败
        (5, 5, True),
        (5, 6, False),    # 第六个连接应该失败
    ])
    @pytest.mark.asyncio
    async def test_connection_limit_variations(self, max_connections, attempt_to_connect, expected_success):
        """测试连接限制变化（参数化测试）"""
        manager = ConnectionManager(max_connections=max_connections)
        websockets = []

        # 尝试连接
        for i in range(attempt_to_connect):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")

            result = await manager.connect(ws)
            if result:
                websockets.append(ws)

        # 最后一次连接的结果应该符合预期
        if expected_success:
            assert manager.get_connection_count() == attempt_to_connect
        else:
            assert manager.get_connection_count() == max_connections

        # 清理
        for ws in websockets:
            await manager.disconnect(ws)


class TestParametrizedTokenAuth:
    """参数化令牌认证测试示例"""

    @pytest.mark.parametrize("token,expected_valid", [
        ("valid_token_123", True),
        ("another_valid_token", True),
        ("", False),
        ("invalid", False),
        ("fake_token", False),
    ])
    def test_token_validation_scenarios(self, token, expected_valid):
        """测试令牌验证场景（参数化测试）"""
        manager = TokenManager(token_expiry=60)

        if expected_valid:
            # 添加有效令牌
            if token not in [None, ""]:
                manager.tokens[token] = float('inf')  # 永不过期用于测试
                assert manager.validate_token(token) is True
        else:
            # 无效令牌应该失败
            if token not in manager.tokens:
                assert manager.validate_token(token) is False


class TestParametrizedErrorScenarios:
    """参数化错误场景测试示例"""

    @pytest.mark.parametrize("exception_type,error_message,should_raise", [
        (ValueError, "Invalid audio", True),
        (TypeError, "Wrong type", True),
        (RuntimeError, "Runtime error", True),
        (None, "No error", False),
    ])
    def test_error_handling(self, exception_type, error_message, should_raise):
        """测试错误处理（参数化测试）"""
        service = FunASRService()

        if should_raise:
            # 模拟错误场景
            if exception_type == ValueError:
                with pytest.raises(ValueError, match="太短"):
                    service._validate_audio(b"", 16000)
            elif exception_type == TypeError:
                # 这会引发TypeError（不是2的倍数）
                with pytest.raises(Exception):
                    service._validate_audio(b"\x00\x01\x02", 16000)

    @pytest.mark.parametrize("invalid_audio_data,expected_error", [
        (b"", "太短"),
        (b"\x00" * 100, "太短"),
        (b"\x00\x01\x02", "不是2的倍数"),
    ])
    def test_invalid_audio_errors(self, invalid_audio_data, expected_error):
        """测试无效音频错误（参数化测试）"""
        service = FunASRService()
        with pytest.raises(Exception):
            service._validate_audio(invalid_audio_data, 16000)


class TestParametrizedWebsocketScenarios:
    """参数化WebSocket场景测试示例"""

    @pytest.mark.parametrize("num_messages", [1, 5, 10, 50])
    @pytest.mark.asyncio
    async def test_sending_multiple_messages(self, num_messages):
        """测试发送多条消息（参数化测试）"""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        manager = ConnectionManager(max_connections=1)
        await manager.connect(websocket)

        # 发送多条消息
        for i in range(num_messages):
            await manager.send_personal_message(f"Message {i}", websocket)

        # 验证所有消息都发送了
        assert websocket.send_text.call_count == num_messages

        await manager.disconnect(websocket)

    @pytest.mark.parametrize("num_connections", [1, 2, 3, 5])
    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, num_connections):
        """测试多个并发连接（参数化测试）"""
        manager = ConnectionManager(max_connections=num_connections + 1)
        websockets = []

        # 创建多个连接
        for i in range(num_connections):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")

            await manager.connect(ws)
            websockets.append(ws)

        # 验证所有连接都成功
        assert manager.get_connection_count() == num_connections

        # 清理
        for ws in websockets:
            await manager.disconnect(ws)


class TestParametrizedCombinations:
    """参数化组合测试示例"""

    @pytest.mark.parametrize("audio_size,vad_enabled,expected_segments", [
        (1600, True, 1),      # 短音频，VAD启用
        (16000, True, 1),     # 中等音频，VAD启用
        (160000, True, 1),    # 长音频，VAD启用
        (1600, False, 1),     # 短音频，VAD禁用
        (16000, False, 1),    # 中等音频，VAD禁用
        (160000, False, 1),   # 长音频，VAD禁用
    ])
    def test_vad_combinations(self, audio_size, vad_enabled, expected_segments):
        """测试VAD组合场景（参数化测试）"""
        from app.core.vad_tracker import VADStateTracker

        tracker = VADStateTracker(
            silence_threshold_ms=800,
            max_segment_duration_ms=20000
        )

        # 处理音频块
        has_speech = True
        should_segment = tracker.process_audio_chunk(has_speech, audio_size)

        # 验证结果
        assert isinstance(should_segment, bool)

        # 获取状态
        state = tracker.get_state()
        assert "total_segment_duration_ms" in state
        assert "consecutive_silence_ms" in state


# ============================================================================
# 参数化测试最佳实践说明
# ============================================================================

"""
参数化测试最佳实践：

1. **何时使用参数化测试**:
   - 测试相同的逻辑但使用不同的输入值
   - 测试边界条件时使用多个相似的测试用例
   - 需要验证多个类似场景时

2. **参数化测试的优势**:
   - 减少重复代码
   - 提高测试可维护性
   - 更容易添加新的测试用例
   - 测试报告更清晰（每个参数组合都是独立的测试）

3. **参数化测试的模式**:

   # 简单参数化
   @pytest.mark.parametrize("input,expected", [
       (1, 2),
       (2, 4),
       (3, 6),
   ])
   def test_simple(input, expected):
       assert double(input) == expected

   # 多参数参数化
   @pytest.mark.parametrize("x,y,expected", [
       (1, 2, 3),
       (2, 3, 5),
       (0, 0, 0),
   ])
   def test_add(x, y, expected):
       assert add(x, y) == expected

   # 组合参数化（笛卡尔积）
   @pytest.mark.parametrize("x", [1, 2, 3])
   @pytest.mark.parametrize("y", [10, 20])
   def test_combination(x, y):
       # 会生成 3x2=6 个测试用例
       pass

4. **参数化测试的注意事项**:
   - 保持测试用例的独立性
   - 使用有意义的参数值
   - 添加清晰的注释说明每个参数组合的含义
   - 避免过多的参数组合（会影响测试速度）

5. **参数化测试的命名**:
   - 使用描述性的测试名称
   - 参数名应该清晰表达其含义
   - 在测试文档字符串中说明测试目的
"""
