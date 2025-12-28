"""
Pytest共享配置和fixtures
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket

# =============================================================================
# 音频生成器fixtures
# =============================================================================

@pytest.fixture
def audio_generator():
    """音频数据生成器"""
    class AudioGenerator:
        @staticmethod
        def generate_silence(duration_ms: int, sample_rate: int = 16000) -> bytes:
            """生成静音音频数据"""
            num_samples = int(duration_ms * sample_rate / 1000)
            audio_array = np.zeros(num_samples, dtype=np.int16)
            return audio_array.tobytes()

        @staticmethod
        def generate_noise(duration_ms: int, sample_rate: int = 16000) -> bytes:
            """生成噪声音频数据"""
            num_samples = int(duration_ms * sample_rate / 1000)
            audio_array = np.random.randint(-32768, 32767, size=num_samples, dtype=np.int16)
            return audio_array.tobytes()

    return AudioGenerator()


@pytest.fixture
def silence_audio(audio_generator):
    """生成100ms的静音音频"""
    return audio_generator.generate_silence(100)


@pytest.fixture
def noise_audio(audio_generator):
    """生成100ms的噪声音频"""
    return audio_generator.generate_noise(100)


# =============================================================================
# WebSocket mock fixtures
# =============================================================================

@pytest.fixture
def mock_websocket():
    """创建Mock WebSocket实例"""
    websocket = Mock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_bytes = AsyncMock()
    websocket.close = AsyncMock()
    websocket.client = Mock(host="127.0.0.1")
    websocket.query_params = {}
    return websocket


@pytest.fixture
def mock_websocket_list():
    """创建多个Mock WebSocket实例"""
    def _create_websockets(count: int):
        websockets = []
        for i in range(count):
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            ws.client = Mock(host=f"127.0.0.{i+1}")
            ws.query_params = {}
            websockets.append(ws)
        return websockets
    return _create_websockets


# =============================================================================
# 服务fixtures
# =============================================================================

@pytest.fixture
def funasr_service():
    """创建FunASR服务实例"""
    from app.services.funasr_service import FunASRService
    service = FunASRService()
    yield service
    # 清理
    try:
        service.cleanup()
    except:
        pass


@pytest.fixture
def connection_manager():
    """创建连接管理器实例"""
    from app.core.websocket import ConnectionManager
    return ConnectionManager(max_connections=2)


@pytest.fixture
def rate_limiter():
    """创建限流器实例"""
    from app.middleware.rate_limit import RateLimiter
    return RateLimiter(max_requests=10, window=60)


@pytest.fixture
def websocket_auth():
    """创建WebSocket认证器实例"""
    from app.middleware.websocket_auth import WebSocketAuth
    return WebSocketAuth(require_auth=False)


# =============================================================================
# FastAPI测试客户端fixtures
# =============================================================================

@pytest.fixture
def test_client():
    """创建FastAPI测试客户端"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# =============================================================================
# VAD相关fixtures
# =============================================================================

@pytest.fixture
def vad_tracker():
    """创建VAD状态跟踪器实例"""
    from app.core.vad_tracker import VADStateTracker
    return VADStateTracker(
        silence_threshold_ms=800,
        max_segment_duration_ms=20000
    )


# =============================================================================
# 测试数据fixtures
# =============================================================================

@pytest.fixture
def test_audio_samples():
    """预定义的测试音频样本"""
    return {
        "empty": b"",
        "too_short": np.random.randint(-32768, 32767, size=100, dtype=np.int16).tobytes(),
        "valid_short": np.random.randint(-32768, 32767, size=1600, dtype=np.int16).tobytes(),
        "valid_medium": np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes(),
        "valid_long": np.random.randint(-32768, 32767, size=160000, dtype=np.int16).tobytes(),
    }


# =============================================================================
# 测试钩子
# =============================================================================

def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line("markers", "slow: 运行时间较长的测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "security: 安全测试")
    config.addinivalue_line("markers", "performance: 性能测试")


@pytest.fixture(autouse=True)
def reset_global_state():
    """每个测试后重置全局状态"""
    yield
    pass


def pytest_collection_modifyitems(config, items):
    """动态修改测试项"""
    # 标记所有异步测试
    import asyncio
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
