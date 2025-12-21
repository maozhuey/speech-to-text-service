from fastapi import APIRouter
import psutil
import time
from ...core.websocket import websocket_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_connections": websocket_manager.get_connection_count(),
        "max_connections": 2,
        "queue_size": 0,  # 暂时没有队列实现
        "memory_usage": psutil.virtual_memory().percent,
        "cpu_usage": psutil.cpu_percent(interval=1),
        "service": "语音转文本服务",
        "version": "1.0.0"
    }