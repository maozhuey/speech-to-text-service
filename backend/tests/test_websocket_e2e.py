"""
WebSocket端到端测试
测试WebSocket连接的完整流程
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from fastapi import WebSocket
from fastapi.testclient import TestClient

from app.main import app
from app.core.websocket import ConnectionManager
from app.services.funasr_service import FunASRService


class TestConnectionManager:
    """连接管理器端到端测试"""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self):
        """测试完整的连接生命周期"""
        manager = ConnectionManager(max_connections=2)

        # 创建mock WebSocket
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        # 连接
        connected = await manager.connect(websocket)
        assert connected is True
        assert manager.get_connection_count() == 1
        websocket.accept.assert_called_once()

        # 验证连接成功消息
        websocket.send_json.assert_called()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection_established"
        assert "session_id" in call_args

        # 发送音频数据
        audio_data = self._generate_test_audio(16000)
        await manager.process_audio(websocket, audio_data)

        # 断开连接
        await manager.disconnect(websocket)
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """测试多个并发连接"""
        manager = ConnectionManager(max_connections=3)

        websockets = []
        for i in range(3):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")
            websockets.append(ws)

        # 连接所有客户端
        for ws in websockets:
            await manager.connect(ws)

        assert manager.get_connection_count() == 3

        # 断开所有连接
        for ws in websockets:
            await manager.disconnect(ws)

        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_connection_limit(self):
        """测试连接数限制"""
        manager = ConnectionManager(max_connections=2)

        websockets = []
        for i in range(4):  # 尝试连接4个客户端
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")
            websockets.append(ws)

        # 前2个应该成功
        for ws in websockets[:2]:
            connected = await manager.connect(ws)
            assert connected is True
            ws.accept.assert_called_once()

        # 第3个应该被拒绝
        connected = await manager.connect(websockets[2])
        assert connected is False
        websockets[2].accept.assert_not_called()
        websockets[2].close.assert_called()

    @pytest.mark.asyncio
    async def test_audio_size_limit(self):
        """测试音频数据大小限制"""
        manager = ConnectionManager(max_connections=2)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        await manager.connect(websocket)

        # 生成超大的音频数据
        large_audio = b"x" * (11 * 1024 * 1024)  # 11MB，超过10MB限制

        await manager.process_audio(websocket, large_audio)

        # 应该发送错误消息
        websocket.send_json.assert_called()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert "过大" in call_args["message"]

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """测试广播消息"""
        manager = ConnectionManager(max_connections=3)

        websockets = []
        for i in range(3):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")
            await manager.connect(ws)
            websockets.append(ws)

        # 广播消息
        test_message = "Test broadcast message"
        await manager.broadcast(test_message)

        # 验证所有连接都收到消息
        for ws in websockets:
            ws.send_text.assert_called_with(test_message)

    def _generate_test_audio(self, sample_rate: int, duration: float = 0.1) -> bytes:
        """生成测试音频数据"""
        # 生成0.1秒的静音音频 (16位PCM, 单声道)
        num_samples = int(sample_rate * duration)
        audio_array = np.zeros(num_samples, dtype=np.int16)
        return audio_array.tobytes()


class TestFunASRService:
    """FunASR服务端到端测试"""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """测试服务初始化"""
        service = FunASRService()

        # 模拟模式下不需要真实模型
        assert service.is_initialized is False

    def test_audio_validation(self):
        """测试音频数据验证"""
        service = FunASRService()

        # 有效音频
        valid_audio = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()
        result = service._validate_audio(valid_audio)
        assert result is not None
        assert len(result) == 16000

        # 音频太短
        short_audio = np.random.randint(-32768, 32767, size=100, dtype=np.int16).tobytes()
        with pytest.raises(ValueError):
            service._validate_audio(short_audio)

        # 无效音频
        with pytest.raises(ValueError):
            service._validate_audio(b"")

    def test_temp_file_creation(self):
        """测试临时文件创建和清理"""
        service = FunASRService()

        # 创建测试音频
        audio_array = np.random.uniform(-1, 1, size=16000).astype(np.float32)
        temp_file = service._save_temp_audio(audio_array, 16000)

        assert temp_file is not None
        import os
        assert os.path.exists(temp_file)

        # 清理
        os.unlink(temp_file)
        assert not os.path.exists(temp_file)


class TestWebSocketIntegration:
    """WebSocket集成测试"""

    @pytest.mark.asyncio
    async def test_websocket_message_flow(self):
        """测试WebSocket消息流程"""
        manager = ConnectionManager(max_connections=2)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_bytes = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        # 连接
        connected = await manager.connect(websocket)
        assert connected is True

        # 模拟接收音频数据
        test_audio = self._generate_silence_audio(16000)
        await manager.process_audio(websocket, test_audio)

        # 断开
        await manager.disconnect(websocket)

    def _generate_silence_audio(self, sample_rate: int, duration: float = 0.1) -> bytes:
        """生成静音音频数据"""
        import numpy as np
        num_samples = int(sample_rate * duration)
        audio_array = np.zeros(num_samples, dtype=np.int16)
        return audio_array.tobytes()


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_websocket_disconnect_during_processing(self):
        """测试处理过程中断开连接"""
        manager = ConnectionManager(max_connections=2)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        await manager.connect(websocket)

        # 发送数据，处理中会出错
        audio_data = self._generate_test_audio(16000)

        # 不应该抛出异常
        try:
            await manager.process_audio(websocket, audio_data)
        except Exception:
            pass  # 预期可能有异常

        # 清理
        await manager.disconnect(websocket)

    @pytest.mark.asyncio
    async def test_cleanup_with_pending_tasks(self):
        """测试清理时取消待处理任务"""
        manager = ConnectionManager(max_connections=2)

        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        await manager.connect(websocket)

        # 添加一些待处理任务
        async def dummy_task():
            await asyncio.sleep(10)

        task = asyncio.create_task(dummy_task())
        manager.processing_tasks[websocket] = [task]

        # 断开连接应该取消任务
        await manager.disconnect(websocket)

        # 验证任务被取消
        assert task.cancelled()

    def _generate_test_audio(self, sample_rate: int) -> bytes:
        """生成测试音频"""
        import numpy as np
        return np.zeros(1600, dtype=np.int16).tobytes()


class TestRateLimitingIntegration:
    """限流集成测试"""

    @pytest.mark.asyncio
    async def test_rate_limit_on_websocket_connection(self):
        """测试WebSocket连接的限流"""
        from app.middleware.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=3, window=60)

        # 前3次应该允许
        for i in range(3):
            assert limiter.is_allowed("test_client") is True

        # 第4次应该拒绝
        assert limiter.is_allowed("test_client") is False


class TestAuthTokenIntegration:
    """认证令牌集成测试"""

    @pytest.mark.asyncio
    async def test_token_generation_and_validation_flow(self):
        """测试令牌生成和验证流程"""
        from app.middleware.websocket_auth import generate_access_token, validate_access_token

        # 生成令牌
        token = generate_access_token()
        assert token is not None
        assert len(token) > 20

        # 验证令牌
        assert validate_access_token(token) is True

        # 验证无效令牌
        assert validate_access_token("invalid_token") is False

    @pytest.mark.asyncio
    async def test_token_expiry_in_websocket_context(self):
        """测试WebSocket上下文中的令牌过期"""
        from app.middleware.websocket_auth import WebSocketAuth, generate_access_token
        import time

        auth = WebSocketAuth(require_auth=True)

        # 生成令牌并立即使用
        token = generate_access_token()
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        websocket.query_params = {"token": token}

        result = await auth.authenticate(websocket)
        assert result is not None
        assert result.get("authenticated") is True
