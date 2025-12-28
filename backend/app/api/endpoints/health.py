from fastapi import APIRouter, Depends, HTTPException
import psutil
import time
from ...core.websocket import websocket_manager
from ...middleware.websocket_auth import WebSocketAuth, get_token_from_query

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
async def extended_health_check(
    token: str = None
):
    """
    扩展健康检查接口

    返回更详细的系统信息，仅用于监控和调试
    需要提供有效的令牌才能访问（当启用认证时）

    Args:
        token: 访问令牌（可选，如果启用了认证则为必需）

    Returns:
        详细的健康检查信息

    Raises:
        HTTPException: 如果令牌无效（当启用认证时）
    """
    # 检查是否启用了扩展健康检查认证
    from ...core.config import settings

    # 如果启用了认证，必须提供有效的令牌
    if settings.require_extended_health_auth:
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide a valid token via 'token' query parameter."
            )
        from ...middleware.websocket_auth import validate_access_token
        if not validate_access_token(token):
            raise HTTPException(status_code=403, detail="Invalid or expired token")
    elif token:
        # 可选认证模式：如果提供了令牌，仍然需要验证
        from ...middleware.websocket_auth import validate_access_token
        if not validate_access_token(token):
            raise HTTPException(status_code=403, detail="Invalid or expired token")

    # 获取系统信息（但限制精度，防止信息泄露）
    try:
        memory = psutil.virtual_memory()
        # 只返回整数百分比，不暴露精确的内存使用情况
        memory_percent = int(memory.percent)

        cpu = psutil.cpu_percent(interval=0.1)
        # 只返回整数百分比
        cpu_percent = int(cpu)
    except Exception as e:
        # 如果获取系统信息失败，返回默认值
        memory_percent = 0
        cpu_percent = 0

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_connections": websocket_manager.get_connection_count(),
        "max_connections": websocket_manager.max_connections,
        "memory_usage_percent": memory_percent,
        "cpu_usage_percent": cpu_percent,
        "service": "speech-to-text",
        "version": "1.0.0"
    }