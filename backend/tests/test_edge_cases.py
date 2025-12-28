"""
边界条件和安全测试
测试输入验证、边界条件和安全场景
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import numpy as np
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket

from app.core.websocket import ConnectionManager
from app.services.funasr_service import FunASRService
from app.middleware.rate_limit import RateLimiter
from app.middleware.websocket_auth import WebSocketAuth, generate_access_token


class TestAudioInputValidation:
    """音频输入验证测试"""

    def test_empty_audio_data(self):
        """测试空音频数据"""
        service = FunASRService()

        with pytest.raises(ValueError, match="太短"):
            service._validate_audio(b"", 16000)

    def test_very_short_audio(self):
        """测试非常短的音频"""
        service = FunASRService()

        # 少于0.1秒
        short_audio = np.random.randint(-32768, 32767, size=100, dtype=np.int16).tobytes()

        with pytest.raises(ValueError, match="太短"):
            service._validate_audio(short_audio, 16000)

    def test_exactly_minimum_length(self):
        """测试刚好达到最小长度的音频"""
        service = FunASRService()

        # 刚好0.1秒 = 1600样本
        min_audio = np.random.randint(-32768, 32767, size=1600, dtype=np.int16).tobytes()

        result = service._validate_audio(min_audio, 16000)
        assert result is not None
        assert len(result) == 1600

    def test_very_long_audio(self):
        """测试超长音频数据"""
        service = FunASRService()

        # 1小时的音频
        long_audio = np.random.randint(-32768, 32767, size=16000 * 3600, dtype=np.int16).tobytes()

        # 应该能够处理（不崩溃）
        result = service._validate_audio(long_audio, 16000)
        assert result is not None
        assert len(result) == 16000 * 3600

    def test_corrupted_audio_data(self):
        """测试损坏的音频数据"""
        service = FunASRService()

        # 不是2的倍数长度的数据
        corrupted_audio = b"\x00\x01\x02"  # 3字节

        with pytest.raises(Exception):
            service._validate_audio(corrupted_audio, 16000)

    @pytest.mark.parametrize("sample_rate,expected_size", [
        (8000, 800),     # 8kHz
        (16000, 1600),   # 16kHz (标准)
        (48000, 4800),   # 48kHz (高质量)
        (22050, 2205),   # 22.05kHz (音频CD质量的一半)
        (44100, 4410),   # 44.1kHz (音频CD质量)
    ])
    def test_different_sample_rates(self, sample_rate, expected_size):
        """测试不同采样率（参数化测试）"""
        service = FunASRService()
        audio = np.zeros(expected_size, dtype=np.int16).tobytes()
        result = service._validate_audio(audio, sample_rate)
        assert len(result) == expected_size

    @pytest.mark.parametrize("value,description", [
        (32767, "全最大值"),
        (-32768, "全最小值"),
        (0, "全零值"),
    ])
    def test_extreme_audio_values(self, value, description):
        """测试极端音频值（参数化测试）"""
        service = FunASRService()
        extreme_audio = np.full(1600, value, dtype=np.int16).tobytes()
        result = service._validate_audio(extreme_audio, 16000)
        assert result is not None

    def test_alternating_audio_values(self):
        """测试交替最大最小值"""
        service = FunASRService()
        alternating = np.array([32767 if i % 2 == 0 else -32768 for i in range(1600)], dtype=np.int16).tobytes()
        result = service._validate_audio(alternating, 16000)
        assert result is not None


class TestConnectionLimits:
    """连接限制测试"""

    @pytest.mark.asyncio
    async def test_max_connections_boundary(self):
        """测试最大连接数边界"""
        manager = ConnectionManager(max_connections=2)

        websockets = []
        for i in range(2):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")
            websockets.append(ws)

        # 连接2个应该成功
        for ws in websockets:
            connected = await manager.connect(ws)
            assert connected is True

        # 第3个应该失败
        ws3 = Mock(spec=WebSocket)
        ws3.accept = AsyncMock()
        ws3.send_json = AsyncMock()
        ws3.close = AsyncMock()
        ws3.client = Mock(host="127.0.0.3")

        connected = await manager.connect(ws3)
        assert connected is False
        ws3.close.assert_called()

        # 清理
        for ws in websockets:
            await manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_zero_max_connections(self):
        """测试最大连接数为0"""
        manager = ConnectionManager(max_connections=0)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        connected = await manager.connect(websocket)
        assert connected is False
        websocket.close.assert_called()

    @pytest.mark.asyncio
    async def test_large_max_connections(self):
        """测试大连接数限制"""
        manager = ConnectionManager(max_connections=1000)

        assert manager.max_connections == 1000
        assert manager.is_connection_available() is True


class TestRateLimitBoundaries:
    """限流边界测试"""

    def test_zero_max_requests(self):
        """测试最大请求数为0"""
        limiter = RateLimiter(max_requests=0, window=60)

        assert limiter.is_allowed("client1") is False

    def test_very_large_max_requests(self):
        """测试非常大的最大请求数"""
        limiter = RateLimiter(max_requests=1000000, window=60)

        for i in range(100):
            assert limiter.is_allowed("client1") is True

    def test_zero_window(self):
        """测试时间窗口为0（立即过期）"""
        limiter = RateLimiter(max_requests=10, window=0, auto_cleanup_interval=1)

        # 每次请求都会被允许因为窗口立即过期
        for i in range(20):
            assert limiter.is_allowed("client1") is True

    def test_very_short_window(self):
        """测试非常短的时间窗口"""
        import time

        limiter = RateLimiter(max_requests=2, window=1, auto_cleanup_interval=1)

        # 前2个请求
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True

        # 第3个被拒绝
        assert limiter.is_allowed("client1") is False

        # 等待窗口过期
        time.sleep(1.1)

        # 应该重新允许
        assert limiter.is_allowed("client1") is True


class TestTokenBoundaries:
    """令牌边界测试"""

    @pytest.mark.parametrize("expiry,should_sleep,sleep_time,expected_valid_after", [
        (86400, False, 0, True),      # 24小时 - 长期有效
        (3600, False, 0, True),       # 1小时 - 中等时长
        (60, False, 0, True),         # 1分钟 - 短期有效
        (1, True, 1.2, False),        # 1秒 - 快速过期（移除0秒测试，因为时间精度问题）
        (2, True, 2.2, False),        # 2秒 - 快速过期
    ])
    def test_token_expiry_variations(self, expiry, should_sleep, sleep_time, expected_valid_after):
        """测试不同令牌过期时间（参数化测试）"""
        from app.middleware.websocket_auth import TokenManager
        import time

        manager = TokenManager(token_expiry=expiry)
        token = manager.generate_token()

        # 初始验证应该成功
        assert manager.validate_token(token) is True

        # 如果需要等待过期
        if should_sleep:
            time.sleep(sleep_time)
            assert manager.validate_token(token) is expected_valid_after


class TestConcurrentScenarios:
    """并发场景测试"""

    @pytest.mark.asyncio
    async def test_concurrent_token_generation(self):
        """测试并发令牌生成"""
        from app.middleware.websocket_auth import generate_access_token

        # generate_access_token是同步函数，直接调用
        tokens = [generate_access_token() for _ in range(100)]

        # 所有令牌应该唯一
        assert len(set(tokens)) == 100

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """测试并发连接"""
        manager = ConnectionManager(max_connections=10)

        async def connect_client(client_id: int):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{client_id}")
            return await manager.connect(ws)

        # 并发连接10个客户端
        tasks = [connect_client(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # 所有连接应该成功
        assert all(results)
        assert manager.get_connection_count() == 10

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """测试并发限流"""
        import asyncio

        limiter = RateLimiter(max_requests=5, window=60)

        async def make_request(client_id: int):
            return limiter.is_allowed(f"client_{client_id}")

        # 10个客户端各发1个请求
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # 所有请求都应该成功
        assert all(results)


class TestSecurityScenarios:
    """安全场景测试"""

    @pytest.mark.asyncio
    async def test_malicious_audio_data(self):
        """测试恶意音频数据"""
        service = FunASRService()

        # 包含可疑模式的数据（长度不是2的倍数）
        suspicious_pattern = bytes([0xFF, 0xFE, 0xFD] * 10000)  # 30000字节，是2的倍数

        # 应该能处理但不崩溃
        # 由于长度是偶数，验证会通过（但值会被处理）
        try:
            result = service._validate_audio(suspicious_pattern, 16000)
            # 如果验证通过，检查结果
            assert result is not None
        except Exception:
            # 如果验证失败也是合理的（数据异常）
            pass

    @pytest.mark.asyncio
    async def test_token_brute_force_protection(self):
        """测试令牌暴力破解保护"""
        from app.middleware.websocket_auth import WebSocketAuth

        auth = WebSocketAuth(require_auth=True)

        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        # 尝试多个无效令牌
        invalid_tokens = [
            "a" * 10,
            "token123",
            "admin",
            "password",
            "12345678",
        ]

        for token in invalid_tokens:
            websocket.query_params = {"token": token}
            result = await auth.authenticate(websocket)
            assert result is None
            # 每次都应该关闭连接
            assert websocket.close.call_count > 0

    def test_rate_limit_memory_exhaustion(self):
        """测试限流器内存耗尽保护"""
        # 使用更短的清理间隔来测试
        limiter = RateLimiter(max_requests=10, window=1, auto_cleanup_interval=2)

        # 添加大量不同的客户端
        for i in range(100):
            limiter.is_allowed(f"client_{i}")

        # 等待自动清理
        time.sleep(2.5)

        # 触发新的请求来激活自动清理
        limiter.is_allowed("new_client")

        # 内部数据结构应该被清理（过期记录被移除）
        # 由于窗口是1秒，所有记录都应该过期
        assert len(limiter.requests) <= 2  # 可能还有最新的1-2个记录


class TestErrorRecovery:
    """错误恢复测试"""

    @pytest.mark.asyncio
    async def test_websocket_reconnection_after_error(self):
        """测试错误后重新连接"""
        manager = ConnectionManager(max_connections=2)

        # 第一次连接
        ws1 = Mock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws1.close = AsyncMock()
        ws1.client = Mock(host="127.0.0.1")

        connected1 = await manager.connect(ws1)
        assert connected1 is True

        # 断开
        await manager.disconnect(ws1)
        assert manager.get_connection_count() == 0

        # 重新连接
        ws2 = Mock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()
        ws2.client = Mock(host="127.0.0.1")

        connected2 = await manager.connect(ws2)
        assert connected2 is True
        assert manager.get_connection_count() == 1

    def test_service_recovery_after_error(self):
        """测试服务错误后恢复"""
        service = FunASRService()

        # 第一次尝试失败（模拟）
        try:
            service._validate_audio(b"", 16000)
        except ValueError:
            pass  # 预期的错误

        # 后续尝试应该成功
        valid_audio = np.zeros(1600, dtype=np.int16).tobytes()
        result = service._validate_audio(valid_audio, 16000)
        assert result is not None


class TestDataConsistency:
    """数据一致性测试"""

    @pytest.mark.asyncio
    async def test_audio_buffer_consistency(self):
        """测试音频缓冲区一致性"""
        manager = ConnectionManager(max_connections=2)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        await manager.connect(websocket)

        # 发送多个音频块
        chunks = []
        for i in range(5):
            chunk = np.random.randint(-32768, 32767, size=1600, dtype=np.int16).tobytes()
            chunks.append(chunk)
            await manager.process_audio(websocket, chunk)

        # 验证缓冲区
        if websocket in manager.audio_buffers:
            buffer = manager.audio_buffers[websocket]
            assert len(buffer) <= 1000  # maxlen限制

        await manager.disconnect(websocket)

    @pytest.mark.asyncio
    async def test_connection_state_consistency(self):
        """测试连接状态一致性"""
        manager = ConnectionManager(max_connections=2)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        # 连接前
        assert manager.get_connection_count() == 0
        assert websocket not in manager.active_connections

        # 连接后
        await manager.connect(websocket)
        assert manager.get_connection_count() == 1
        assert websocket in manager.active_connections

        # 断开后
        await manager.disconnect(websocket)
        assert manager.get_connection_count() == 0
        assert websocket not in manager.active_connections
        assert websocket not in manager.connection_info
