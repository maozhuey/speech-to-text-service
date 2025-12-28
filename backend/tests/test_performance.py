"""
性能基准测试
测试系统在各种场景下的性能表现
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import asyncio
import time
import numpy as np
import gc
import psutil
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket

from app.core.websocket import ConnectionManager
from app.core.vad_tracker import VADStateTracker
from app.services.funasr_service import FunASRService


class TestPerformanceBaseline:
    """性能基准测试"""

    def test_vad_tracker_performance(self):
        """测试VAD跟踪器性能"""
        tracker = VADStateTracker(
            silence_threshold_ms=800,
            max_segment_duration_ms=20000
        )

        # 生成大量音频块
        num_iterations = 10000
        audio_size_bytes = 1600  # 100ms音频

        start_time = time.time()

        for _ in range(num_iterations):
            tracker.process_audio_chunk(
                has_speech=True,
                audio_size_bytes=audio_size_bytes
            )

        elapsed = time.time() - start_time
        avg_time_ms = (elapsed / num_iterations) * 1000

        # 验证性能要求：每次处理应该小于1ms
        assert avg_time_ms < 1.0, f"VAD处理太慢: {avg_time_ms:.3f}ms"

    def test_audio_validation_performance(self):
        """测试音频验证性能"""
        service = FunASRService()

        # 生成标准测试音频
        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        num_iterations = 1000
        start_time = time.time()

        for _ in range(num_iterations):
            service._validate_audio(audio_data, 16000)

        elapsed = time.time() - start_time
        avg_time_ms = (elapsed / num_iterations) * 1000

        # 验证性能
        assert avg_time_ms < 1.0, f"音频验证太慢: {avg_time_ms:.3f}ms"

    def test_rate_limiter_performance(self):
        """测试限流器性能"""
        from app.middleware.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=10000, window=60)

        num_requests = 10000
        start_time = time.time()

        for i in range(num_requests):
            limiter.is_allowed(f"client_{i % 1000}")

        elapsed = time.time() - start_time
        avg_time_ms = (elapsed / num_requests) * 1000

        # 验证性能
        assert avg_time_ms < 0.1, f"限流检查太慢: {avg_time_ms:.3f}ms"

    def test_token_generation_performance(self):
        """测试令牌生成性能"""
        from app.middleware.websocket_auth import generate_access_token

        num_tokens = 1000
        start_time = time.time()

        tokens = [generate_access_token() for _ in range(num_tokens)]

        elapsed = time.time() - start_time
        avg_time_ms = (elapsed / num_tokens) * 1000

        # 验证性能
        assert avg_time_ms < 1.0, f"令牌生成太慢: {avg_time_ms:.3f}ms"

        # 验证唯一性
        assert len(set(tokens)) == num_tokens, "令牌应该唯一"


class TestMemoryPerformance:
    """内存性能测试"""

    @pytest.mark.memory
    @pytest.mark.slow
    def test_memory_usage_during_connections(self):
        """测试连接时的内存使用"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        manager = ConnectionManager(max_connections=50)

        # 创建和清理50个连接
        for cycle in range(10):
            websockets = []
            for i in range(50):
                ws = Mock(spec=WebSocket)
                ws.accept = AsyncMock()
                ws.send_json = AsyncMock()
                ws.close = AsyncMock()
                ws.client = Mock(host=f"192.168.1.{cycle % 256}.{i % 256}")
                # 注意：这里不使用await，因为是mock
                manager.active_connections.append(ws)
                manager.connection_info[ws] = {
                    "connected_at": time.time(),
                    "last_activity": time.time(),
                    "session_id": f"session_{cycle}_{i}"
                }
                manager.audio_buffers[ws] = []
                manager.processing_tasks[ws] = []
                manager.audio_segments[ws] = []
                manager.audio_sizes[ws] = 0
                websockets.append(ws)

            # 清理
            for ws in websockets:
                manager.active_connections.remove(ws)
                manager.connection_info.pop(ws, None)
                manager.audio_buffers.pop(ws, None)
                manager.processing_tasks.pop(ws, None)
                manager.audio_segments.pop(ws, None)
                manager.audio_sizes.pop(ws, None)

        # 强制垃圾回收
        gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024

        # 内存增长不应该超过50MB
        assert memory_increase < 50, f"内存增长过多: {memory_increase:.2f}MB"


class TestLatencyPerformance:
    """延迟性能测试"""

    @pytest.mark.slow
    def test_vad_latency_percentiles(self):
        """测试VAD处理延迟的百分位数"""
        tracker = VADStateTracker(
            silence_threshold_ms=800,
            max_segment_duration_ms=20000
        )

        latencies = []
        num_samples = 10000

        for _ in range(num_samples):
            start = time.perf_counter()
            tracker.process_audio_chunk(
                has_speech=True,
                audio_size_bytes=1600
            )
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)  # 转换为毫秒

        # 计算百分位数
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        # 验证延迟要求
        assert p50 < 0.1, f"P50延迟太高: {p50:.6f}ms"
        assert p95 < 0.5, f"P95延迟太高: {p95:.6f}ms"
        assert p99 < 1.0, f"P99延迟太高: {p99:.6f}ms"


class TestConcurrencyPerformance:
    """并发性能测试"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_vad_processing(self):
        """测试并发VAD处理性能"""
        # 创建多个跟踪器模拟并发
        num_trackers = 10
        trackers = [
            VADStateTracker(
                silence_threshold_ms=800,
                max_segment_duration_ms=20000
            )
            for _ in range(num_trackers)
        ]

        num_iterations = 1000
        start_time = time.time()

        async def process_tracker(tracker):
            for _ in range(num_iterations):
                tracker.process_audio_chunk(
                    has_speech=True,
                    audio_size_bytes=1600
                )

        await asyncio.gather(*[process_tracker(t) for t in trackers])

        elapsed = time.time() - start_time
        total_operations = num_trackers * num_iterations
        ops_per_second = total_operations / elapsed

        # 验证吞吐量 - 降低预期值
        assert ops_per_second > 50000, f"吞吐量太低: {ops_per_second:.0f} ops/s"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """测试并发限流性能"""
        from app.middleware.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=1000, window=60)

        num_clients = 100
        num_requests_per_client = 100

        async def check_limits(client_id):
            for _ in range(num_requests_per_client):
                limiter.is_allowed(f"client_{client_id}")

        start_time = time.time()

        await asyncio.gather(*[
            check_limits(i) for i in range(num_clients)
        ])

        elapsed = time.time() - start_time
        total_requests = num_clients * num_requests_per_client
        requests_per_second = total_requests / elapsed

        # 验证吞吐量
        assert requests_per_second > 5000, f"限流吞吐量太低: {requests_per_second:.0f} req/s"


class TestStressTests:
    """压力测试"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """测试持续负载"""
        manager = ConnectionManager(max_connections=10)

        # 模拟持续使用
        num_cycles = 100
        connections_per_cycle = 5

        for cycle in range(num_cycles):
            websockets = []
            for i in range(connections_per_cycle):
                ws = Mock(spec=WebSocket)
                ws.accept = AsyncMock()
                ws.send_json = AsyncMock()
                ws.close = AsyncMock()
                ws.client = Mock(host=f"127.0.0.{i}")
                # 直接添加到列表，不使用await
                manager.active_connections.append(ws)
                manager.connection_info[ws] = {
                    "connected_at": time.time(),
                    "last_activity": time.time(),
                    "session_id": f"session_{cycle}_{i}"
                }
                manager.audio_buffers[ws] = []
                manager.processing_tasks[ws] = []
                manager.audio_segments[ws] = []
                manager.audio_sizes[ws] = 0
                websockets.append(ws)

            # 处理音频
            for ws in websockets:
                # 直接添加到缓冲区
                audio_data = np.random.randint(-32768, 32767, size=1600, dtype=np.int16).tobytes()
                manager.audio_buffers[ws].append(audio_data)

            # 清理
            for ws in websockets:
                manager.active_connections.remove(ws)
                manager.connection_info.pop(ws, None)
                manager.audio_buffers.pop(ws, None)
                manager.processing_tasks.pop(ws, None)
                manager.audio_segments.pop(ws, None)
                manager.audio_sizes.pop(ws, None)

        # 验证最终状态正常
        assert manager.get_connection_count() == 0


class TestResourceLimits:
    """资源限制测试"""

    @pytest.mark.memory
    def test_audio_size_limit(self):
        """测试音频大小限制"""
        manager = ConnectionManager(max_connections=2)

        # 验证限制
        assert manager.max_audio_size_per_connection == 10 * 1024 * 1024

        # 计算限制（10MB）
        limit = manager.max_audio_size_per_connection

        # 验证限制值合理
        assert limit == 10485760  # 10MB
        assert limit > 0
        assert limit < 100 * 1024 * 1024  # 不应该超过100MB


class TestPerformanceDegradation:
    """性能退化测试"""

    @pytest.mark.slow
    def test_no_performance_degradation_over_time(self):
        """测试长时间运行没有严重性能退化"""
        tracker = VADStateTracker(
            silence_threshold_ms=800,
            max_segment_duration_ms=20000
        )

        # 分批处理，比较每批的性能
        num_batches = 10
        operations_per_batch = 1000

        baseline_avg = None

        for batch in range(num_batches):
            start_time = time.time()

            for _ in range(operations_per_batch):
                tracker.process_audio_chunk(
                    has_speech=True,
                    audio_size_bytes=1600
                )

            elapsed = time.time() - start_time
            avg_time_ms = (elapsed / operations_per_batch) * 1000

            if baseline_avg is None:
                baseline_avg = avg_time_ms
            else:
                # 性能退化不应该超过200%（允许3倍变化，考虑系统负载波动）
                degradation = (avg_time_ms - baseline_avg) / baseline_avg if baseline_avg > 0 else 0
                assert degradation < 2.0, f"性能退化: {degradation:.1%}"
