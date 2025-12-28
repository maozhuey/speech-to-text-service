from fastapi import APIRouter
import psutil
import time
from ...core.websocket import websocket_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    健康检查接口

    返回服务基本状态信息，不暴露敏感的系统配置信息
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_connections": websocket_manager.get_connection_count(),
        "service": "speech-to-text",
        "version": "1.0.0"
    }

@router.get("/health/extended")
async def extended_health_check():
    """
    扩展健康检查接口

    返回更详细的系统信息，仅用于监控和调试
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_connections": websocket_manager.get_connection_count(),
        "max_connections": websocket_manager.max_connections,
        "memory_usage_percent": psutil.virtual_memory().percent,
        "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
        "service": "speech-to-text",
        "version": "1.0.0"
    }