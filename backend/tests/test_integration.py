"""
集成测试：端到端测试VAD断句功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import asyncio
import numpy as np
import time
from app.core.vad_tracker import VADStateTracker
from app.core.websocket import ConnectionManager
from app.services.funasr_service import FunASRService


class TestIntegration:
    """集成测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.vad_tracker = VADStateTracker(
            silence_threshold_ms=800,
            max_segment_duration_ms=20000
        )
        self.connection_manager = ConnectionManager(max_connections=2)
        self.funasr_service = FunASRService()

    def generate_audio_bytes(self, duration_ms: int, energy_level: float = 0.1) -> bytes:
        """生成模拟音频数据"""
        num_samples = int(duration_ms * 16000 / 1000)
        audio = np.random.randn(num_samples).astype(np.float32) * energy_level
        audio_int16 = (audio * 32768).astype(np.int16)
        return audio_int16.tobytes()

    def test_vad_tracker_end_to_end(self):
        """测试VAD跟踪器端到端场景"""
        print("  测试场景：用户说话 -> 停顿 -> 断句")

        # 场景1：用户说话2秒
        speech_2s = self.generate_audio_bytes(2000, energy_level=0.2)
        result1 = self.vad_tracker.process_audio_chunk(has_speech=True, audio_size_bytes=len(speech_2s))
        assert result1 is False, "2秒语音不应该触发断句"
        assert self.vad_tracker.total_segment_duration_ms == 2000
        print("    ✓ 2秒语音累积")

        # 场景2：用户继续说话1秒
        speech_1s = self.generate_audio_bytes(1000, energy_level=0.2)
        result2 = self.vad_tracker.process_audio_chunk(has_speech=True, audio_size_bytes=len(speech_1s))
        assert result2 is False, "再1秒语音不应该触发断句"
        assert self.vad_tracker.total_segment_duration_ms == 3000
        print("    ✓ 累积3秒语音")

        # 场景3：用户停顿800ms
        silence_800ms = self.generate_audio_bytes(800, energy_level=0.0001)
        result3 = self.vad_tracker.process_audio_chunk(has_speech=False, audio_size_bytes=len(silence_800ms))
        assert result3 is True, "800ms停顿应该触发断句"
        print("    ✓ 800ms停顿触发断句")

        # 场景4：重置后继续
        self.vad_tracker.reset()
        speech_new = self.generate_audio_bytes(1000, energy_level=0.2)
        result4 = self.vad_tracker.process_audio_chunk(has_speech=True, audio_size_bytes=len(speech_new))
        assert result4 is False, "重置后1秒语音不应该触发断句"
        assert self.vad_tracker.total_segment_duration_ms == 1000
        print("    ✓ 重置后正常工作")

        print("✓ VAD跟踪器端到端测试通过")

    def test_timeout_scenario(self):
        """测试超时强制断句场景"""
        print("  测试场景：用户持续说话超过20秒")

        # 持续说话20秒
        for i in range(10):
            speech_2s = self.generate_audio_bytes(2000, energy_level=0.2)
            result = self.vad_tracker.process_audio_chunk(has_speech=True, audio_size_bytes=len(speech_2s))
            if i < 9:
                assert result is False, f"第{i+1}个2秒块不应该触发断句"
            else:
                assert result is True, "第10个2秒块（20秒）应该触发超时断句"

        print("    ✓ 20秒后正确触发超时断句")
        print("✓ 超时场景测试通过")

    def test_short_pause_scenario(self):
        """测试短暂停顿场景"""
        print("  测试场景：说话中有短暂停顿")

        # 说话1秒
        speech_1s = self.generate_audio_bytes(1000, energy_level=0.2)
        result1 = self.vad_tracker.process_audio_chunk(has_speech=True, audio_size_bytes=len(speech_1s))
        assert result1 is False

        # 停顿400ms（小于阈值）
        pause_400ms = self.generate_audio_bytes(400, energy_level=0.0001)
        result2 = self.vad_tracker.process_audio_chunk(has_speech=False, audio_size_bytes=len(pause_400ms))
        assert result2 is False, "400ms停顿不应该触发断句"
        print("    ✓ 400ms停顿未触发断句")

        # 继续说话1秒
        speech_1s_again = self.generate_audio_bytes(1000, energy_level=0.2)
        result3 = self.vad_tracker.process_audio_chunk(has_speech=True, audio_size_bytes=len(speech_1s_again))
        assert result3 is False, "短暂停后继续说话不应该触发断句"
        assert self.vad_tracker.consecutive_silence_ms == 0, "静音计数应该被重置"
        assert self.vad_tracker.total_segment_duration_ms == 2000, "应该累积2秒语音"
        print("    ✓ 短暂停后继续累积语音")

        print("✓ 短暂停场景测试通过")

    def test_connection_manager_initialization(self):
        """测试连接管理器初始化"""
        assert self.connection_manager.max_connections == 2
        assert self.connection_manager.get_connection_count() == 0
        assert self.connection_manager.is_connection_available() == True
        print("✓ 连接管理器初始化测试通过")

    def test_vad_service_integration(self):
        """测试VAD服务集成"""
        async def run_test():
            print("  测试场景：VAD服务与跟踪器集成")

            # 生成音频数据
            speech_audio = self.generate_audio_bytes(1000, energy_level=0.3)
            silence_audio = self.generate_audio_bytes(1000, energy_level=0.0001)

            # 使用VAD服务检测
            speech_result = await self.funasr_service.detect_voice_activity_realtime(speech_audio)
            assert speech_result["success"] is True
            assert speech_result["has_speech"] is True
            print("    ✓ VAD服务正确检测语音")

            silence_result = await self.funasr_service.detect_voice_activity_realtime(silence_audio)
            assert silence_result["success"] is True
            assert silence_result["has_speech"] is False
            print("    ✓ VAD服务正确检测静音")

            # 集成测试：VAD服务 -> VAD跟踪器
            # 模拟真实场景：检测语音 -> 跟踪器处理
            tracker = VADStateTracker(silence_threshold_ms=800, max_segment_duration_ms=20000)

            # 连续说话2秒
            for _ in range(2):
                audio = self.generate_audio_bytes(1000, energy_level=0.2)
                vad_result = await self.funasr_service.detect_voice_activity_realtime(audio)
                should_segment = tracker.process_audio_chunk(
                    has_speech=vad_result["has_speech"],
                    audio_size_bytes=len(audio)
                )
                assert should_segment is False

            # 停顿900ms
            silence = self.generate_audio_bytes(900, energy_level=0.0001)
            vad_result = await self.funasr_service.detect_voice_activity_realtime(silence)
            should_segment = tracker.process_audio_chunk(
                has_speech=vad_result["has_speech"],
                audio_size_bytes=len(silence)
            )
            assert should_segment is True, "900ms停顿应该触发断句"
            print("    ✓ VAD服务与跟踪器集成正常")

            print("✓ VAD服务集成测试通过")

        asyncio.run(run_test())

    def test_performance_baseline(self):
        """测试性能基准"""
        print("  测试场景：VAD处理性能")

        # 测试VAD跟踪器处理速度
        num_iterations = 1000
        start_time = time.time()

        tracker = VADStateTracker()
        audio_bytes = self.generate_audio_bytes(100, energy_level=0.1)

        for i in range(num_iterations):
            tracker.process_audio_chunk(has_speech=(i % 10 < 7), audio_size_bytes=len(audio_bytes))

        elapsed = time.time() - start_time
        throughput = num_iterations / elapsed

        print(f"    ✓ 处理{num_iterations}次音频块耗时{elapsed:.3f}秒")
        print(f"    ✓ 吞吐量: {throughput:.0f} 次/秒")

        # 验证性能要求：每次处理应该小于1ms
        avg_time_ms = (elapsed / num_iterations) * 1000
        assert avg_time_ms < 1, f"平均处理时间{avg_time_ms:.3f}ms超过1ms阈值"
        print(f"    ✓ 平均处理时间{avg_time_ms:.3f}ms满足要求")

        print("✓ 性能基准测试通过")


def run_tests():
    """运行所有集成测试"""
    print("VAD断句功能集成测试")
    print("=" * 50)

    test_class = TestIntegration()

    tests = [
        ("VAD跟踪器端到端", test_class.test_vad_tracker_end_to_end),
        ("超时场景", test_class.test_timeout_scenario),
        ("短暂停场景", test_class.test_short_pause_scenario),
        ("连接管理器初始化", test_class.test_connection_manager_initialization),
        ("VAD服务集成", test_class.test_vad_service_integration),
        ("性能基准", test_class.test_performance_baseline),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        try:
            test_class.setup_method()  # 重新初始化
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")

    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
