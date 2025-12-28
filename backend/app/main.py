from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.endpoints import health, info
from app.core.websocket import websocket_manager
from app.core.config import settings
from app.middleware.rate_limit import RateLimiter
from app.middleware.websocket_auth import WebSocketAuth, generate_access_token

# 初始化限流器（每分钟最多60个WebSocket连接尝试）
rate_limiter = RateLimiter(max_requests=60, window=60)

# 初始化认证器（可选模式：仅当提供token时验证）
ws_auth = WebSocketAuth(require_auth=False)

# WebSocket消息大小限制（10MB）
MAX_WS_MESSAGE_SIZE = 10 * 1024 * 1024

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

# 配置CORS（安全配置，从环境变量读取允许的域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=settings.get_allowed_methods_list(),
    allow_headers=settings.get_allowed_headers_list(),
    expose_headers=["Content-Type"],
    max_age=600,  # 预检请求缓存时间（秒）
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求的日志中间件"""
    start_time = time.time()

    # 记录请求开始
    logger.info(f"请求开始: {request.method} {request.url.path}")

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 添加响应头并记录完成
    response.headers["X-Process-Time"] = str(f"{process_time:.3f}")
    logger.info(
        f"请求完成: {request.method} {request.url.path} - "
        f"状态码: {response.status_code} - "
        f"耗时: {process_time:.3f}秒"
    )

    return response

# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(info.router, prefix="/api/v1", tags=["info"])

# 挂载静态文件目录（前端资源）
# 获取backend目录，然后向上找到正确的frontend目录
backend_dir = os.path.dirname(os.path.abspath(__file__))
# 从backend目录向上两级到apps目录，然后找到frontend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(backend_dir)), "语音转文本服务", "frontend"))

if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")
    logger.info(f"前端静态文件目录已挂载: {frontend_path}")
else:
    logger.warning(f"前端目录不存在: {frontend_path}")
    # 尝试直接使用相对路径
    rel_frontend_path = os.path.abspath("../frontend")
    if os.path.exists(rel_frontend_path):
        app.mount("/frontend", StaticFiles(directory=rel_frontend_path), name="frontend")
        logger.info(f"使用相对前端路径: {rel_frontend_path}")


@app.get("/api/v1/token", tags=["auth"])
async def generate_token():
    """
    生成WebSocket访问令牌

    返回一个可用于WebSocket连接的访问令牌。
    如果启用认证，客户端需要在连接时提供此令牌。
    """
    token = generate_access_token()
    return JSONResponse({
        "success": True,
        "token": token,
        "message": "请使用此令牌连接WebSocket: ws://host/ws?token=YOUR_TOKEN"
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，处理实时音频流和语音识别"""

    # 获取客户端IP用于限流
    client_ip = websocket.client.host if websocket.client else "unknown"

    # 检查限流
    if not rate_limiter.is_allowed(client_ip):
        await websocket.close(
            code=1013,
            reason=f"Rate limit exceeded. Please try again later. "
                   f"Max {rate_limiter.max_requests} connections per {rate_limiter.window} seconds."
        )
        logger.warning(f"拒绝WebSocket连接：客户端 {client_ip} 超过限流阈值")
        return

    # 可选认证
    user_info = await ws_auth.authenticate(websocket)
    if user_info is None:
        # 认证失败且连接已关闭
        return

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

                # 验证消息大小
                if len(data) > MAX_WS_MESSAGE_SIZE:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"消息过大：{len(data)} 字节，最大允许 {MAX_WS_MESSAGE_SIZE} 字节"
                    })
                    logger.warning(
                        f"客户端 {client_ip} 发送过大的消息: {len(data)} 字节"
                    )
                    continue

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
                except (WebSocketDisconnect, ConnectionResetError) as disconnect_err:
                    # 连接已断开，退出处理
                    logger.debug(f"发送错误消息时连接断开: {disconnect_err}")
                    break
                except Exception as send_err:
                    # 其他发送错误
                    logger.error(f"发送错误消息失败: {send_err}")
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
        <p>Web界面: <a href="/frontend/index.html">/frontend/index.html</a></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )