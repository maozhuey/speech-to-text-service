from fastapi import WebSocket
from typing import List, Dict, Any, Optional
import json
import logging
import asyncio
import time
from collections import deque
import uuid

from app.services.funasr_service import funasr_service, FunASRService
from app.core.vad_tracker import VADStateTracker
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketDisconnectError(Exception):
    """WebSocket断开连接异常"""
    pass

class ConnectionManager:
    """
    WebSocket 连接管理器

    支持多模型选择：
    - 通过 model 参数指定使用哪个识别模型
    - 验证模型有效性
    - 错误处理
    """

    def __init__(self, max_connections: int = 2):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}
        self.max_connections = max_connections
        self.audio_buffers: Dict[WebSocket, deque] = {}
        self.processing_tasks: Dict[WebSocket, List[asyncio.Task]] = {}
        self.audio_segments: Dict[WebSocket, List[bytes]] = {}
        # 安全限制：每个连接最大音频数据大小（10MB）
        self.max_audio_size_per_connection = 10 * 1024 * 1024
        # 当前连接的音频数据大小
        self.audio_sizes: Dict[WebSocket, int] = {}
        # VAD状态跟踪器（每个连接一个）
        self.vad_trackers: Dict[WebSocket, VADStateTracker] = {}
        # 每个连接的 FunASR 服务实例（支持不同模型）
        self.funasr_services: Dict[WebSocket, FunASRService] = {}

    async def connect(self, websocket: WebSocket, model: Optional[str] = None) -> bool:
        """
        接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            model: 指定的模型名称（offline 或 streaming），默认使用配置中的默认模型

        Returns:
            连接是否成功建立
        """
        try:
            # 先检查连接数限制
            if len(self.active_connections) >= self.max_connections:
                try:
                    await websocket.close(code=1013, reason=f"已达到最大连接数限制 ({self.max_connections})")
                except (WebSocketDisconnect, RuntimeError, OSError) as e:
                    logger.debug(f"关闭连接失败（连接可能已断开）: {e}")
                return False

            # 验证模型参数
            model_name = model or settings.default_model
            model_config = settings.get_model_config(model_name)

            if model_config is None:
                await websocket.close(code=4002, reason=f"Invalid model: {model_name}")
                logger.warning(f"无效的模型名称: {model_name}")
                return False

            if not model_config.get("enabled", True):
                await websocket.close(code=4003, reason=f"Model {model_name} is not enabled")
                logger.warning(f"模型 {model_name} 未启用")
                return False

            # 接受连接
            await websocket.accept()

            # 创建该连接专用的 FunASR 服务实例
            funasr_instance = FunASRService(default_model=model_name)

            # 初始化指定模型
            try:
                await funasr_instance.initialize(model_name)
            except Exception as e:
                await websocket.close(code=4003, reason=f"Failed to load model: {model_name}")
                logger.error(f"加载模型 {model_name} 失败: {e}")
                return False

            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "connected_at": time.time(),
                "last_activity": time.time(),
                "session_id": f"session_{int(time.time() * 1000)}",
                "model": model_name
            }
            self.audio_buffers[websocket] = deque(maxlen=1000)  # 保存最近1000个音频块
            self.processing_tasks[websocket] = []
            self.audio_segments[websocket] = []  # 用于累积音频数据
            self.audio_sizes[websocket] = 0  # 初始化音频数据大小
            self.funasr_services[websocket] = funasr_instance  # 保存该连接的服务实例

            # 初始化VAD跟踪器
            if settings.vad_enabled:
                self.vad_trackers[websocket] = VADStateTracker(
                    silence_threshold_ms=settings.vad_silence_threshold_ms,
                    max_segment_duration_ms=settings.vad_max_segment_duration_ms
                )
                logger.info(f"VAD已启用，阈值: {settings.vad_silence_threshold_ms}ms")

            # 发送连接成功消息
            await websocket.send_json({
                "type": "connection_established",
                "session_id": self.connection_info[websocket]["session_id"],
                "model": model_name,
                "model_display_name": model_config.get("display_name", model_name),
                "message": "连接成功"
            })

            logger.info(f"WebSocket 连接建立 (模型: {model_name})，当前连接数: {len(self.active_connections)}")
            return True

        except Exception as e:
            logger.error(f"连接建立失败: {e}", exc_info=True)
            try:
                await websocket.close(code=1011, reason="服务器内部错误")
            except (WebSocketDisconnect, RuntimeError, OSError) as close_err:
                logger.debug(f"关闭连接失败（连接可能已断开）: {close_err}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            self.audio_buffers.pop(websocket, None)

            # 取消所有正在处理的任务，并等待完成
            if websocket in self.processing_tasks:
                tasks = self.processing_tasks.pop(websocket, [])
                for task in tasks:
                    task.cancel()
                    try:
                        # 等待任务完成，最多等待5秒
                        await asyncio.wait_for(task, timeout=5.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        # 任务被取消或超时，这是预期的
                        pass
                    except Exception as e:
                        logger.warning(f"取消任务时发生错误: {e}")

            self.audio_segments.pop(websocket, None)
            self.audio_sizes.pop(websocket, None)
            self.vad_trackers.pop(websocket, None)  # 清理VAD跟踪器

            # 清理该连接的 FunASR 服务实例
            if websocket in self.funasr_services:
                try:
                    self.funasr_services[websocket].cleanup()
                except Exception as e:
                    logger.warning(f"清理 FunASR 服务时出错: {e}")
                self.funasr_services.pop(websocket, None)

            logger.info(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")

    async def process_audio(self, websocket: WebSocket, audio_data: bytes):
        """处理音频数据"""
        try:
            # 更新活动时间
            if websocket in self.connection_info:
                self.connection_info[websocket]["last_activity"] = time.time()

            # 检查音频数据大小限制
            if websocket in self.audio_sizes:
                if self.audio_sizes[websocket] + len(audio_data) > self.max_audio_size_per_connection:
                    await websocket.send_json({
                        "type": "error",
                        "message": "音频数据过大，请先停止录音再重新开始"
                    })
                    return

                # 更新音频数据大小
                self.audio_sizes[websocket] += len(audio_data)

            # 将音频数据添加到缓冲区和音频片段列表
            if websocket in self.audio_buffers:
                self.audio_buffers[websocket].append(audio_data)

            if websocket in self.audio_segments:
                self.audio_segments[websocket].append(audio_data)
                # 更新累积音频大小
                total_size = sum(len(chunk) for chunk in self.audio_segments[websocket])
                # 清空音频片段时会减少总大小
                if total_size > self.max_audio_size_per_connection:
                    self.audio_segments[websocket] = []
                    await websocket.send_json({
                        "type": "error",
                        "message": "累积音频数据过大，已自动清空缓冲区"
                    })
                    return

            # VAD智能断句或固定时长断句
            should_segment = False
            segment_reason = ""

            # 获取该连接的 FunASR 服务实例
            funasr_instance = self.funasr_services.get(websocket, funasr_service)

            if settings.vad_enabled and websocket in self.vad_trackers:
                # 使用VAD智能断句
                try:
                    vad_result = await funasr_instance.detect_voice_activity_realtime(audio_data)
                    has_speech = vad_result.get('has_speech', True)
                    should_segment = self.vad_trackers[websocket].process_audio_chunk(
                        has_speech,
                        len(audio_data)
                    )
                    segment_reason = "VAD检测"
                except Exception as e:
                    logger.warning(f"VAD检测失败，回退到固定时长: {e}")
                    # 回退到固定时长断句
                    total_size = sum(len(chunk) for chunk in self.audio_segments[websocket])
                    should_segment = total_size >= 160000
                    segment_reason = "固定时长"
            else:
                # 使用固定时长断句（约5秒）
                total_size = sum(len(chunk) for chunk in self.audio_segments[websocket])
                should_segment = total_size >= 160000
                segment_reason = "固定时长"

            # 触发断句
            if should_segment and self.audio_segments[websocket]:
                logger.info(f"触发断句（{segment_reason}），音频数据: {sum(len(chunk) for chunk in self.audio_segments[websocket])} 字节")

                # 创建异步任务进行语音识别
                task = asyncio.create_task(
                    self._recognize_audio_segment(websocket, self.audio_segments[websocket][:])
                )

                # 保存任务引用
                if websocket in self.processing_tasks:
                    self.processing_tasks[websocket].append(task)

                # 清空音频片段列表
                self.audio_segments[websocket] = []

                # 重置VAD跟踪器
                if settings.vad_enabled and websocket in self.vad_trackers:
                    self.vad_trackers[websocket].reset()

        except Exception as e:
            logger.error(f"音频处理错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"音频处理失败: {str(e)}"
            })

    async def _recognize_audio_segment(self, websocket: WebSocket, audio_chunks: List[bytes]):
        """异步识别音频片段"""
        try:
            # 将音频片段合并
            combined_audio = b''.join(audio_chunks)

            # 减少音频大小计数（已处理的数据）
            if websocket in self.audio_sizes:
                self.audio_sizes[websocket] -= len(combined_audio)
                self.audio_sizes[websocket] = max(0, self.audio_sizes[websocket])

            # 发送处理中状态
            await websocket.send_json({
                "type": "processing",
                "message": "正在识别语音..."
            })

            # 获取该连接的 FunASR 服务实例
            funasr_instance = self.funasr_services.get(websocket, funasr_service)

            # 调用FunASR进行识别
            result = await funasr_instance.recognize_speech(combined_audio, sample_rate=16000)

            # 发送识别结果
            await websocket.send_json({
                "type": "recognition_result",
                **result
            })

        except asyncio.CancelledError:
            logger.info("语音识别任务被取消")
        except Exception as e:
            logger.error(f"语音识别错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"语音识别失败: {str(e)}"
            })

    async def process_audio_final(self, websocket: WebSocket):
        """处理最后累积的音频数据（用户停止录音时调用）"""
        try:
            if websocket in self.audio_segments and self.audio_segments[websocket]:
                task = asyncio.create_task(
                    self._recognize_audio_segment(websocket, self.audio_segments[websocket][:])
                )

                if websocket in self.processing_tasks:
                    self.processing_tasks[websocket].append(task)

                self.audio_segments[websocket] = []

        except Exception as e:
            logger.error(f"处理最终音频数据错误: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"处理最终音频失败: {str(e)}"
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