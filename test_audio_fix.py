#!/usr/bin/env python3
"""
测试音频格式修复效果
"""
import asyncio
import websockets
import json
import numpy as np

async def test_audio_conversion():
    """测试音频转换是否正常工作"""
    print("=== 测试音频格式修复 ===\n")

    uri = "ws://localhost:8002/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")

            # 等待连接确认
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📩 服务器响应: {data}")

            # 发送初始化消息
            init_msg = {
                "type": "init",
                "sample_rate": 16000,
                "channels": 1,
                "chunk_size": 1024
            }
            await websocket.send(json.dumps(init_msg))
            print("✅ 初始化消息已发送")

            # 测试1: 发送正确的PCM音频数据
            print("\n测试1: 发送正确的PCM音频数据...")
            sample_rate = 16000
            duration = 2.0  # 2秒
            frequency = 440  # A4音符

            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = (np.sin(2 * np.pi * frequency * t) * 16383).astype(np.int16)

            # 分块发送
            chunk_size = 1024 * 2  # 2KB chunks
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await websocket.send(chunk.tobytes())

                # 等待处理结果
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    if data.get('type') == 'recognition_result':
                        print(f"   📝 识别结果: {data.get('text', '')}")
                        break
                except asyncio.TimeoutError:
                    continue

            # 等待最终识别结果
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"   📝 最终结果: {data}")
            except asyncio.TimeoutError:
                print("   ⚠️ 未收到识别结果")

            # 测试2: 发送静音数据
            print("\n测试2: 发送静音数据...")
            silence_data = np.zeros(16000, dtype=np.int16)  # 1秒静音
            await websocket.send(silence_data.tobytes())

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                text = data.get('text', '')
                print(f"   📝 静音识别结果: \"{text}\"")
                if text in ['没有没有没有没有', '好的好的好的好的']:
                    print("   ⚠️ 仍然返回固定结果，可能需要进一步调试")
                else:
                    print("   ✅ 识别结果正常")
            except asyncio.TimeoutError:
                print("   ⚠️ 未收到静音识别结果")

            print("\n=== 测试完成 ===")
            print("请在浏览器中访问 http://localhost:8081 测试实际录音功能")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    asyncio.run(test_audio_conversion())

if __name__ == "__main__":
    main()