from fastapi import WebSocket
from typing import List, Dict, Any
import json
import logging
import asyncio
import time
from collections import deque

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self, max_connections: int = 2):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}
        self.max_connections = max_connections
        self.audio_buffers: Dict[WebSocket, deque] = {}

    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        try:
            await websocket.accept()

            if len(self.active_connections) >= self.max_connections:
                await websocket.send_json({
                    "type": "connection_rejected",
                    "message": f"已达到最大连接数限制 ({self.max_connections})"
                })
                await websocket.close()
                return False

            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "connected_at": time.time(),
                "last_activity": time.time(),
                "session_id": f"session_{int(time.time() * 1000)}"
            }
            self.audio_buffers[websocket] = deque(maxlen=1000)  # 保存最近1000个音频块

            # 发送连接成功消息
            await websocket.send_json({
                "type": "connection_established",
                "session_id": self.connection_info[websocket]["session_id"],
                "message": "连接成功"
            })

            logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
            return True

        except Exception as e:
            logger.error(f"连接建立失败: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            self.audio_buffers.pop(websocket, None)
            logger.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")

    async def process_audio(self, websocket: WebSocket, audio_data: bytes):
        """处理音频数据"""
        try:
            # 更新活动时间
            if websocket in self.connection_info:
                self.connection_info[websocket]["last_activity"] = time.time()

            # 将音频数据添加到缓冲区
            if websocket in self.audio_buffers:
                self.audio_buffers[websocket].append(audio_data)

            # TODO: 实际的音频处理逻辑
            # 这里应该调用FunASR进行语音识别
            # 暂时返回模拟数据

            # 模拟处理延迟
            await asyncio.sleep(0.1)

            # 发送模拟识别结果
            await websocket.send_json({
                "type": "recognition_result",
                "text": "这是模拟的识别结果",
                "speaker": "speaker_1",
                "is_final": True,
                "confidence": 0.95,
                "timestamp": {
                    "start": time.time() - 1,
                    "end": time.time()
                }
            })

        except Exception as e:
            logger.error(f"音频处理错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"音频处理失败: {str(e)}"
            })

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    async def broadcast(self, message: str):
        """广播消息给所有连接"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                await self.disconnect(connection)

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)

    def is_connection_available(self) -> bool:
        """检查是否可以接受新连接"""
        return len(self.active_connections) < self.max_connections

    async def cleanup_inactive_connections(self, timeout: int = 300):
        """清理不活跃的连接（5分钟超时）"""
        current_time = time.time()
        inactive_connections = []

        for websocket, info in self.connection_info.items():
            if current_time - info["last_activity"] > timeout:
                inactive_connections.append(websocket)

        for websocket in inactive_connections:
            await self.disconnect(websocket)
            logger.info(f"清理不活跃连接: {info.get('session_id', 'unknown')}")

# 创建全局连接管理器实例
websocket_manager = ConnectionManager(max_connections=2)