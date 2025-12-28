from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.endpoints import health, info
from app.core.websocket import websocket_manager
from app.core.config import settings

# 创建日志目录
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="语音转文本服务",
    description="基于FunASR的中文语音转文本基础服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，方便开发测试
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(info.router, prefix="/api/v1", tags=["info"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，处理实时音频流和语音识别"""
    # 建立连接
    connected = await websocket_manager.connect(websocket)

    # 如果连接未被接受，直接返回
    if not connected:
        return

    try:
        while True:
            # 接收客户端发送的数据
            try:
                data = await websocket.receive_bytes()
                await websocket_manager.process_audio(websocket, data)
            except WebSocketDisconnect as e:
                logger.info(f"客户端断开连接，关闭代码: {e.code}")
                break
            except Exception as e:
                logger.error(f"处理音频数据失败: {e}", exc_info=True)
                # 如果是连接断开相关的错误，退出循环
                if "disconnect" in str(e).lower() or "connection" in str(e).lower() or str(e).isdigit():
                    break
                # 发送错误消息给客户端
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"音频处理失败: {str(e)}"
                    })
                except:
                    # 如果发送失败，说明连接已断开
                    break
                # 不中断连接，继续接收数据
                continue

    except WebSocketDisconnect as e:
        logger.info(f"客户端主动断开连接，关闭代码: {e.code}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        # 确保连接被正确清理
        await websocket_manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """提供简单的前端页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>语音转文本服务</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>语音转文本服务</h1>
        <p>服务运行正常！</p>
        <p>API文档: <a href="/docs">/docs</a></p>
        <p>Web界面: <a href="/frontend">/frontend</a></p>
    </body>
    </html>
    """

@app.get("/frontend", response_class=HTMLResponse)
async def get_frontend():
    """返回前端界面"""
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="前端文件未找到，请先构建前端界面")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )