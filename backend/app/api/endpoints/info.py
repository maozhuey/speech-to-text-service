from fastapi import APIRouter

router = APIRouter()

@router.get("/info")
async def service_info():
    """服务信息接口"""
    return {
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
        "supported_languages": ["zh-CN"],
        "max_connections": 2,
        "audio_format": {
            "sample_rate": 16000,
            "channels": 1,
            "bit_depth": 16,
            "format": "PCM"
        },
        "endpoints": {
            "websocket": "/ws",
            "health": "/api/v1/health",
            "info": "/api/v1/info"
        },
        "documentation": "/docs"
    }