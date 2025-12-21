#!/usr/bin/env python3
"""
调试FunASR语音识别问题
"""
import os
import sys
import tempfile
import wave
import numpy as np

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.app.services.funasr_service import funasr_service

def create_test_audio_with_text(text="测试"):
    """创建包含模拟语音的音频文件"""
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)

    sample_rate = 16000
    duration = 2.0  # 2秒

    # 生成更复杂的信号模拟不同文本
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # 根据文本生成不同的频率模式
    if "测试" in text or text == "test":
        # 模拟"测试"的频率模式
        frequencies = [300, 600, 450, 800]  # 测:300Hz 试:600Hz
    elif "你好" in text:
        # 模拟"你好"的频率模式
        frequencies = [250, 500]  # 你:250Hz 好:500Hz
    else:
        # 默认频率
        frequencies = [400, 800]

    audio_data = np.zeros_like(t)

    for i, freq in enumerate(frequencies):
        amplitude = 0.3 / (i + 1)
        # 添加包络模拟语音节奏
        envelope = np.ones_like(t)
        if i < len(frequencies) - 1:
            segment_length = len(t) // len(frequencies)
            start = i * segment_length
            end = min((i + 1) * segment_length, len(t))
            envelope[:start] = 0.1
            envelope[start:end] = 1.0
            envelope[end:] = 0.1

        audio_data += amplitude * envelope * np.sin(2 * np.pi * freq * t)

    # 添加一些噪音，使音频更真实
    noise = np.random.normal(0, 0.02, len(t))
    audio_data += noise

    # 转换为16位整数
    audio_data = np.clip(audio_data, -1, 1)
    audio_data = (audio_data * 32767).astype(np.int16)

    with wave.open(temp_file.name, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

    return temp_file.name

async def test_asr_pipeline():
    """测试完整的ASR流程"""
    print("=== 调试FunASR语音识别 ===\n")

    try:
        # 初始化服务
        print("1. 初始化FunASR服务...")
        await funasr_service.initialize()
        print("   ✅ 服务初始化成功")

        # 测试不同的音频文件
        test_cases = [
            ("空音频", None),  # 空数据
            ("短音频", b'\x00' * 1000),  # 很短的音频
            ("静音", b'\x00' * 64000),  # 静音音频
            ("随机噪音", np.random.randint(-1000, 1000, 64000, dtype=np.int16).tobytes()),
        ]

        # 添加测试音频文件
        for i, (name, audio_data) in enumerate(test_cases):
            print(f"\n2.{i+1} 测试{name}:")

            if name == "空音频":
                # 创建临时音频文件
                temp_file = create_test_audio_with_text("测试")
                with open(temp_file, 'rb') as f:
                    audio_data = f.read()
                os.unlink(temp_file)

            try:
                result = await funasr_service.recognize_speech(audio_data)
                print(f"   结果: {result}")

                if result.get('success', False):
                    text = result.get('text', '')
                    print(f"   识别文本: \"{text}\"")

                    # 检查是否是固定的结果
                    if text in ['没有没有没有没有', '好的好的好的好的', '嗯嗯嗯嗯']:
                        print(f"   ⚠️  可能返回固定结果: {text}")
                    else:
                        print(f"   ✅ 识别结果正常: {text}")
                else:
                    print(f"   ❌ 识别失败: {result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"   ❌ 测试失败: {e}")

        # 直接测试ModelScope pipeline
        print(f"\n3. 直接测试ModelScope pipeline:")
        model_path = "/Users/hanchanglin/AI编程代码库/apps/语音转文本服务/models/damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"

        temp_file = create_test_audio_with_text("你好世界")
        print(f"   测试音频: {temp_file}")

        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        asr_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model=model_path
        )

        # 直接调用pipeline
        result = asr_pipeline(temp_file)
        print(f"   Pipeline直接结果: {result}")

        # 测试标点符号处理
        if result and isinstance(result, list) and len(result) > 0:
            text = result[0].get('text', '')
            if text:
                print(f"   原始识别文本: \"{text}\"")

                # 测试标点符号模型
                try:
                    punc_model_path = "/Users/hanchanglin/AI编程代码库/apps/语音转文本服务/models/damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
                    punc_pipeline = pipeline(
                        task=Tasks.punctuation,
                        model=punc_model_path
                    )

                    punc_result = punc_pipeline(text)
                    print(f"   标点符号处理结果: {punc_result}")

                    if isinstance(punc_result, dict) and 'text' in punc_result:
                        print(f"   最终文本: \"{punc_result['text']}\"")
                        if punc_result['text'] in ['没有没有没有没有。', '好的好的好的好的。']:
                            print("   ⚠️  标点符号处理后返回固定结果!")

                except Exception as e:
                    print(f"   标点符号处理失败: {e}")

        # 清理临时文件
        os.unlink(temp_file)

    except Exception as e:
        print(f"❌ 调试过程失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    import asyncio
    asyncio.run(test_asr_pipeline())

if __name__ == "__main__":
    main()