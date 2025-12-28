#!/usr/bin/env python3
"""测试VAD状态跟踪器"""
import sys
import os

# 添加backend目录到Python路径
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_path)

from app.core.vad_tracker import VADStateTracker


def ms_to_bytes(ms: int, sample_rate: int = 16000) -> int:
    """将毫秒转换为16位PCM字节数"""
    return int(ms * sample_rate * 2 / 1000)


def test_vad_state_tracker():
    """测试VAD状态跟踪器"""
    print("=== 测试VAD状态跟踪器 ===\n")

    # 创建跟踪器
    tracker = VADStateTracker(
        silence_threshold_ms=800,
        max_segment_duration_ms=20000
    )

    # 测试1: 正常说话停顿后断句
    print("测试1: 正常说话停顿后断句")
    result1 = tracker.process_audio_chunk(True, ms_to_bytes(400))   # 400ms语音
    print(f"  400ms语音 -> 触发断句: {result1} (预期: False)")
    assert not result1, "400ms语音不应触发断句"

    result2 = tracker.process_audio_chunk(False, ms_to_bytes(400))  # 400ms静音，总计400ms
    print(f"  400ms静音 -> 触发断句: {result2} (预期: False)")
    assert not result2, "400ms静音不应触发断句"

    result3 = tracker.process_audio_chunk(False, ms_to_bytes(500))  # 500ms静音，总计900ms
    print(f"  500ms静音 -> 触发断句: {result3} (预期: True)")
    assert result3, "900ms静音应该触发断句"
    print("  ✅ 测试1通过\n")

    # 重置跟踪器
    tracker.reset()

    # 测试2: 短暂停顿不断句
    print("测试2: 短暂停顿不断句")
    tracker.process_audio_chunk(True, ms_to_bytes(1000))  # 1秒语音
    result = tracker.process_audio_chunk(False, ms_to_bytes(400))  # 400ms静音
    print(f"  400ms短停顿 -> 触发断句: {result} (预期: False)")
    assert not result, "400ms短停顿不应触发断句"
    print("  ✅ 测试2通过\n")

    # 重置跟踪器
    tracker.reset()

    # 测试3: 超时强制断句
    print("测试3: 超时强制断句（模拟连续说话）")
    for i in range(20):  # 20秒，每次1秒
        result = tracker.process_audio_chunk(True, ms_to_bytes(1000))
        if result:
            print(f"  第{i+1}秒 -> 触发断句: {result}")
            break
    assert result, "20秒后应该强制断句"
    print("  ✅ 测试3通过\n")

    # 测试4: 状态获取
    print("测试4: 状态获取")
    tracker.reset()
    tracker.process_audio_chunk(True, ms_to_bytes(500))
    tracker.process_audio_chunk(False, ms_to_bytes(300))
    state = tracker.get_state()
    print(f"  状态: {state}")
    assert state['consecutive_silence_ms'] == 300
    assert state['total_segment_duration_ms'] == 500
    print("  ✅ 测试4通过\n")

    print("=== 所有测试通过! ===")


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===\n")

    tracker = VADStateTracker(silence_threshold_ms=800)

    # 测试: 开头静音不应触发断句
    print("测试: 开头静音不应触发断句")
    result = tracker.process_audio_chunk(False, ms_to_bytes(1000))
    print(f"  1000ms开头静音 -> 触发断句: {result} (预期: False)")
    assert not result, "开头静音不应触发断句"
    print("  ✅ 边界测试通过\n")


if __name__ == "__main__":
    try:
        test_vad_state_tracker()
        test_edge_cases()
        print("\n✅ 所有测试通过!")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
