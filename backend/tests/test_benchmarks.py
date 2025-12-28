"""
性能基准测试配置
用于CI/CD中的性能回归检测
"""

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import numpy as np
import time
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket

from app.core.vad_tracker import VADStateTracker
from app.core.websocket import ConnectionManager
from app.services.funasr_service import FunASRService
from app.middleware.rate_limit import RateLimiter


class TestBenchmarks:
    """性能基准测试（用于CI/CD性能回归检测）"""

    def benchmark_vad_tracker_processing(self, benchmark):
        """VAD跟踪器处理性能基准"""
        tracker = VADStateTracker(
            silence_threshold_ms=800,
            max_segment_duration_ms=20000
        )

        audio_size_bytes = 1600  # 100ms音频

        def process_audio():
            tracker.process_audio_chunk(
                has_speech=True,
                audio_size_bytes=audio_size_bytes
            )

        benchmark(process_audio)

    def benchmark_audio_validation(self, benchmark):
        """音频验证性能基准"""
        service = FunASRService()
        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        benchmark(service._validate_audio, audio_data, 16000)

    def benchmark_rate_limiting(self, benchmark):
        """限流器性能基准"""
        limiter = RateLimiter(max_requests=10000, window=60)

        def check_limit():
            limiter.is_allowed("test_client")

        benchmark(check_limit)

    def benchmark_token_generation(self, benchmark):
        """令牌生成性能基准"""
        from app.middleware.websocket_auth import generate_access_token

        benchmark(generate_access_token)

    @pytest.mark.asyncio
    async def benchmark_websocket_message_send(self, benchmark):
        """WebSocket消息发送性能基准"""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock(host="127.0.0.1")

        manager = ConnectionManager(max_connections=1)
        await manager.connect(websocket)

        async def send_message():
            await manager.send_personal_message("Test message", websocket)

        # benchmark不直接支持async，所以使用自定义包装
        import asyncio

        def run_sync():
            asyncio.run(send_message())

        benchmark(run_sync)

        await manager.disconnect(websocket)


# 性能回归阈值配置
PERFORMANCE_THRESHOLDS = {
    "vad_tracker_processing": {
        "min": 10000,  # 最小 ops/s
        "max": 0.001,   # 最大平均时间（秒）
        "regression": 20,  # 回归阈值（百分比）
    },
    "audio_validation": {
        "min": 1000,
        "max": 0.001,
        "regression": 20,
    },
    "rate_limiting": {
        "min": 100000,
        "max": 0.00001,
        "regression": 20,
    },
    "token_generation": {
        "min": 1000,
        "max": 0.001,
        "regression": 20,
    },
}


class TestPerformanceProfiles:
    """性能分析测试"""

    @pytest.mark.parametrize("num_iterations", [100, 1000, 10000])
    def test_vad_performance_profile(self, num_iterations):
        """VAD性能分析（不同迭代次数）"""
        tracker = VADStateTracker()
        audio_size_bytes = 1600

        start_time = time.perf_counter()

        for _ in range(num_iterations):
            tracker.process_audio_chunk(True, audio_size_bytes)

        elapsed = time.perf_counter() - start_time
        ops_per_second = num_iterations / elapsed

        print(f"\nVAD Performance ({num_iterations} iterations):")
        print(f"  Total time: {elapsed:.4f}s")
        print(f"  Ops per second: {ops_per_second:.0f}")
        print(f"  Avg time per op: {(elapsed/num_iterations)*1000:.4f}ms")

        # 性能要求（根据迭代次数调整）
        min_ops = 10000 if num_iterations == 10000 else 50000
        assert ops_per_second > min_ops, f"Performance too low: {ops_per_second:.0f} ops/s"

    @pytest.mark.parametrize("concurrent_operations", [1, 5, 10])
    @pytest.mark.asyncio
    async def test_concurrent_performance_profile(self, concurrent_operations):
        """并发性能分析"""
        import asyncio

        tracker = VADStateTracker()
        num_iterations = 1000

        async def process_audio():
            for _ in range(num_iterations):
                tracker.process_audio_chunk(True, 1600)

        start_time = time.perf_counter()

        await asyncio.gather(*[process_audio() for _ in range(concurrent_operations)])

        elapsed = time.perf_counter() - start_time
        total_operations = concurrent_operations * num_iterations
        ops_per_second = total_operations / elapsed

        print(f"\nConcurrent Performance ({concurrent_operations} concurrent):")
        print(f"  Total time: {elapsed:.4f}s")
        print(f"  Total ops: {total_operations}")
        print(f"  Ops per second: {ops_per_second:.0f}")


# 用于pytest-benchmark插件配置
def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line(
        "markers", "benchmark: 性能基准测试"
    )
    config.addinivalue_line(
        "markers", "profile: 性能分析测试"
    )


# 如果安装了pytest-benchmark，会自动发现benchmark参数
# 运行命令：
# pytest tests/test_benchmarks.py --benchmark-only --benchmark-json=benchmark.json
