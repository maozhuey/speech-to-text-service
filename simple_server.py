#!/usr/bin/env python3
"""
简化的语音转文本服务器
不依赖FastAPI，使用基本的Python库
"""

import asyncio
import websockets
import json
import logging
import time
import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import urllib.parse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SimpleSpeechServer:
    """简化的语音转文本服务器"""

    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.active_connections = set()
        self.max_connections = 2

    async def handle_websocket(self, websocket, path):
        """处理WebSocket连接"""
        # 检查连接限制
        if len(self.active_connections) >= self.max_connections:
            await websocket.send(json.dumps({
                "type": "connection_rejected",
                "message": f"已达到最大连接数限制 ({self.max_connections})"
            }))
            await websocket.close()
            return

        # 接受连接
        self.active_connections.add(websocket)
        session_id = f"session_{int(time.time() * 1000)}"

        # 发送连接成功消息
        await websocket.send(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "message": "连接成功"
        }))

        logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")

        try:
            async for message in websocket:
                # 处理音频数据
                await self.process_audio(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket连接正常关闭")
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
        finally:
            self.active_connections.discard(websocket)
            logger.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")

    async def process_audio(self, websocket, audio_data):
        """处理音频数据（模拟）"""
        # 模拟处理延迟
        await asyncio.sleep(0.1)

        # 发送模拟识别结果
        result = {
            "type": "recognition_result",
            "text": "这是模拟的识别结果",
            "speaker": "speaker_1",
            "is_final": True,
            "confidence": 0.95,
            "timestamp": {
                "start": time.time() - 1,
                "end": time.time()
            }
        }

        try:
            await websocket.send(json.dumps(result))
        except Exception as e:
            logger.error(f"发送结果失败: {e}")

    async def start_websocket_server(self):
        """启动WebSocket服务器"""
        logger.info(f"启动WebSocket服务器: ws://{self.host}:{self.port + 1}/ws")

        # 创建WebSocket处理器
        async def handler(websocket, path):
            if path == "/ws":
                await self.handle_websocket(websocket, path)

        server = await websockets.serve(
            handler,
            self.host,
            self.port + 1  # 使用8001端口作为WebSocket
        )
        await server.wait_closed()

    def start_http_server(self):
        """启动HTTP服务器提供前端页面"""
        class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory="../frontend", **kwargs)

            def do_GET(self):
                if self.path == "/":
                    self.path = "/index.html"
                elif self.path == "/api/v1/health":
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    health_data = {
                        "status": "healthy",
                        "timestamp": time.time(),
                        "active_connections": len(self.active_connections),
                        "max_connections": 2,
                        "service": "语音转文本服务",
                        "version": "1.0.0"
                    }
                    self.wfile.write(json.dumps(health_data, ensure_ascii=False).encode('utf-8'))
                    return
                elif self.path == "/api/v1/info":
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    info_data = {
                        "name": "语音转文本基础服务",
                        "version": "1.0.0",
                        "description": "基于FunASR的中文语音转文本基础服务",
                        "features": [
                            "实时语音识别",
                            "说话人分离",
                            "自动标点添加",
                            "时间戳支持",
                            "WebSocket实时通信",
                            "并发连接控制"
                        ],
                        "websocket_url": f"ws://{self.host}:{self.port + 1}/ws"
                    }
                    self.wfile.write(json.dumps(info_data, ensure_ascii=False).encode('utf-8'))
                    return

                return super().do_GET()

        server = HTTPServer((self.host, self.port), CustomHTTPRequestHandler)
        logger.info(f"启动HTTP服务器: http://{self.host}:{self.port}")
        server.serve_forever()

async def main():
    """主函数"""
    print("语音转文本服务 - 简化版本")
    print("=" * 40)
    print("服务地址: http://localhost:8000")
    print("WebSocket: ws://localhost:8001/ws")
    print("按 Ctrl+C 停止服务")
    print("=" * 40)

    # 创建服务器实例
    server = SimpleSpeechServer()

    # 启动HTTP服务器（在单独线程中）
    http_server = Thread(target=server.start_http_server, daemon=True)
    http_server.start()

    # 启动WebSocket服务器
    try:
        await server.start_websocket_server()
    except KeyboardInterrupt:
        logger.info("服务器已停止")

if __name__ == "__main__":
    asyncio.run(main())