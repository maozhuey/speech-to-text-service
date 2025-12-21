#!/usr/bin/env python3
"""
测试实时音频识别
"""
import asyncio
import websockets
import json

async def test_realtime_audio():
    """测试实时音频流处理"""
    print("=== 测试实时音频识别 ===\n")

    uri = "ws://localhost:8002/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")

            # 等待连接确认
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📩 服务器响应: {data}")

            print("\n请在前端页面 (http://localhost:8081) 开始录音测试")
            print("我将监听服务器的识别结果...")

            # 监听识别结果
            result_count = 0
            while result_count < 10:  # 监听前10个结果
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)

                    if data.get('type') == 'recognition_result':
                        text = data.get('text', '')
                        if text:
                            print(f"📝 识别结果 {result_count + 1}: \"{text}\"")
                            result_count += 1

                        # 检查是否还有固定结果问题
                        if text in ['没有没有没有没有', '好的好的好的好的']:
                            print("⚠️  仍然返回固定结果")
                        elif text:
                            print("✅ 识别结果正常")

                    elif data.get('type') == 'error':
                        print(f"❌ 服务器错误: {data.get('message', 'Unknown error')}")

                except asyncio.TimeoutError:
                    print("\n⏰ 30秒内没有收到识别结果")
                    break

            print(f"\n=== 测试完成 ===")
            print(f"收到 {result_count} 个识别结果")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    asyncio.run(test_realtime_audio())

if __name__ == "__main__":
    main()