# 语音转文本服务设计文档

## 系统架构设计

### 整体架构图
```
┌─────────────────────────────────────────────────────┐
│                前端 Web 界面                          │
│  ┌─────────────────────────────────────────────┐   │
│  │           UI Components                    │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │      Audio Input Control            │   │   │
│  │  │      Text Display Area              │   │   │
│  │  │      Speaker Tags                   │   │   │
│  │  │      Timestamp Display              │   │   │
│  │  │      Action Buttons                 │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────┐   │
│  │  │      WebSocket Client               │   │   │
│  │  │      Audio Stream Manager           │   │   │
│  │  │      Text Renderer                  │   │   │
│  │  │      UI Controller                  │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                          │ WebSocket (ws://127.0.0.1:8000/ws)
                          ▼
┌─────────────────────────────────────────────────────┐
│                 后端服务架构                           │
│  ┌─────────────────────────────────────────────┐   │
│  │            API Gateway                      │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │        FastAPI Application          │   │   │
│  │  │        WebSocket Handler            │   │   │
│  │  │        Connection Manager           │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │          音频处理管道                         │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │        Audio Buffer Manager         │   │   │
│  │  │        Audio Preprocessor           │   │   │
│  │  │        Stream Splitter              │   │   │
│  │  │        Format Converter             │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │          语音识别引擎                         │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │         FunASR Integration          │   │   │
│  │  │         Speech Recognition          │   │   │
│  │  │         Punctuation Prediction      │   │   │
│  │  │         Speaker Diarization         │   │   │
│  │  │         Timestamp Extraction        │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │          数据管理模块                         │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │        Result Formatter             │   │   │
│  │  │        History Manager              │   │   │
│  │  │        Export Service               │   │   │
│  │  │        Cache Manager                │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 核心组件设计

#### 1. WebSocket连接管理器
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.max_connections = 2

    async def connect(self, websocket: WebSocket)
    async def disconnect(self, websocket: WebSocket)
    async def send_personal_message(self, message: str, websocket: WebSocket)
    async def broadcast(self, message: str)
    def is_connection_available(self) -> bool
```

#### 2. 音频流处理器
```python
class AudioStreamProcessor:
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.buffer_size = 1024

    async def process_audio_chunk(self, audio_data: bytes)
    def preprocess_audio(self, audio_data: bytes) -> np.ndarray
    def split_stream(self, audio_data: np.ndarray) -> List[np.ndarray]
    def convert_format(self, audio_data: np.ndarray) -> bytes
```

#### 3. FunASR集成引擎
```python
class FunASREngine:
    def __init__(self):
        self.model = self.load_model()
        self.punctuation_model = self.load_punctuation_model()
        self.diarization_model = self.load_diarization_model()

    async def recognize_speech(self, audio_data: np.ndarray) -> RecognitionResult
    async def add_punctuation(self, text: str) -> str
    async def diarize_speakers(self, audio_data: np.ndarray) -> List[SpeakerSegment]
    def extract_timestamps(self, audio_data: np.ndarray) -> List[Timestamp]
```

## 数据流设计

### 音频处理流程
```
音频输入 (Web Audio API)
        │
        ▼
WebSocket传输 (二进制数据)
        │
        ▼
音频缓冲区管理
        │
        ▼
音频预处理 (降噪、增益、重采样)
        │
        ▼
流式分割 (固定大小chunks)
        │
        ▼
FunASR语音识别
        │
        ▼
后处理 (标点添加、说话人分离、时间戳)
        │
        ▼
结果格式化
        │
        ▼
WebSocket返回 (JSON格式)
        │
        ▼
前端渲染显示
```

### 消息格式设计

#### 客户端发送格式
```json
{
    "type": "audio_chunk",
    "data": "base64编码的音频数据",
    "timestamp": 1234567890,
    "sequence_id": 123
}
```

#### 服务端返回格式
```json
{
    "type": "recognition_result",
    "text": "识别到的文本内容",
    "speaker": "speaker_1",
    "is_final": true,
    "timestamp": {
        "start": 1234567890,
        "end": 1234567895
    },
    "punctuation": {
        "text": "识别到的文本内容。",
        "has_punctuation": true
    },
    "confidence": 0.95
}
```

#### 连接状态消息
```json
{
    "type": "connection_status",
    "status": "connected|disconnected|error",
    "message": "状态描述信息",
    "timestamp": 1234567890
}
```

## 前端架构设计

### 组件结构
```
src/
├── index.html              # 主页面
├── css/
│   └── styles.css          # 样式文件
├── js/
│   ├── app.js              # 主应用入口
│   ├── websocket.js        # WebSocket客户端
│   ├── audio.js            # 音频处理
│   ├── ui.js               # UI控制
│   └── utils.js            # 工具函数
└── assets/
    └── icons/              # 图标资源
```

### 核心JavaScript模块

#### 1. WebSocket客户端
```javascript
class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.onMessage = null;
        this.onStatusChange = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
    }

    connect() { /* 连接逻辑 */ }
    disconnect() { /* 断开逻辑 */ }
    sendAudioData(audioData) { /* 发送音频数据 */ }
    handleReconnect() { /* 重连逻辑 */ }
}
```

#### 2. 音频处理模块
```javascript
class AudioProcessor {
    constructor() {
        this.mediaRecorder = null;
        this.audioContext = null;
        this.stream = null;
        this.chunkSize = 1024;
    }

    async initAudio() { /* 初始化音频 */ }
    startRecording() { /* 开始录音 */ }
    stopRecording() { /* 停止录音 */ }
    processAudioChunk(chunk) { /* 处理音频块 */ }
}
```

#### 3. UI控制器
```javascript
class UIController {
    constructor() {
        this.textDisplay = document.getElementById('text-display');
        this.speakerColors = {};
        this.currentSpeakerIndex = 0;
    }

    updateConnectionStatus(status) { /* 更新连接状态 */ }
    displayRecognitionResult(result) { /* 显示识别结果 */ }
    addSpeakerTag(speaker, text) { /* 添加说话人标签 */ }
    addTimestamp(timestamp) { /* 添加时间戳 */ }
    copyAllText() { /* 复制所有文本 */ }
    clearDisplay() { /* 清空显示 */ }
}
```

## 性能优化设计

### 1. 并发连接控制
```python
class ConnectionLimiter:
    def __init__(self, max_connections=2):
        self.max_connections = max_connections
        self.active_connections = set()
        self.connection_queue = asyncio.Queue()

    async def acquire_connection(self) -> bool
    async def release_connection(self, connection_id: str)
    def get_queue_size(self) -> int
```

### 2. 内存管理策略
- **音频缓冲区**：使用循环缓冲区限制内存使用
- **结果缓存**：LRU缓存最近1000条识别结果
- **垃圾回收**：定期清理过期的连接和数据
- **内存监控**：实时监控内存使用情况

### 3. CPU优化策略
- **异步处理**：使用asyncio实现非阻塞处理
- **批量处理**：合并小的音频块减少处理次数
- **模型预热**：启动时预加载模型避免冷启动
- **并行处理**：利用多核CPU并行处理不同任务

### 4. 网络优化
- **压缩传输**：使用gzip压缩音频数据
- **心跳检测**：定期发送心跳保持连接活跃
- **缓冲策略**：客户端和服务端都使用缓冲区
- **断线重连**：智能重连机制避免频繁重连

## 说话人分离设计

### 说话人识别流程
```
音频流输入
     │
     ▼
语音活动检测 (VAD)
     │
     ▼
音频段分割
     │
     ▼
说话人嵌入提取
     │
     ▼
聚类分析
     │
     ▼
说话人标签分配
     │
     ▼
结果输出
```

### 说话人标签管理
```python
class SpeakerManager:
    def __init__(self):
        self.speaker_colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"
        ]
        self.active_speakers = {}
        self.speaker_counter = 0

    def get_speaker_color(self, speaker_id: str) -> str
    def register_speaker(self, speaker_id: str) -> str
    def get_speaker_label(self, speaker_id: str) -> str
    def update_speaker_activity(self, speaker_id: str, timestamp: float)
```

## 错误处理设计

### 1. 连接错误处理
```python
async def handle_websocket_error(websocket: WebSocket, error: Exception):
    if isinstance(error, ConnectionClosedOK):
        logger.info("Normal connection closure")
    elif isinstance(error, ConnectionClosedError):
        logger.error(f"Abnormal connection closure: {error.code}")
        await notify_client_reconnect(websocket)
    else:
        logger.error(f"Unexpected error: {error}")
        await send_error_message(websocket, str(error))
```

### 2. 音频处理错误
```python
class AudioProcessingError(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

# 错误代码定义
class ErrorCodes:
    AUDIO_FORMAT_INVALID = "AUDIO_FORMAT_INVALID"
    AUDIO_TOO_SHORT = "AUDIO_TOO_SHORT"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    RECOGNITION_FAILED = "RECOGNITION_FAILED"
```

### 3. 前端错误处理
```javascript
class ErrorHandler {
    static handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        this.showUserNotification('连接出现问题，正在尝试重连...');
        this.attemptReconnect();
    }

    static handleAudioError(error) {
        console.error('Audio error:', error);
        this.showUserNotification('麦克风访问失败，请检查权限设置');
    }

    static showUserNotification(message) {
        // 显示用户友好的错误提示
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            document.body.removeChild(notification);
        }, 5000);
    }
}
```

## 监控和日志设计

### 1. 性能监控指标
- **响应时间**：API响应时间分布
- **识别准确率**：语音识别准确率统计
- **连接状态**：活跃连接数和队列长度
- **资源使用**：CPU、内存使用情况
- **错误率**：各类错误的发生频率

### 2. 日志记录格式
```python
import logging
import json

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_recognition_request(self, session_id: str, audio_length: float):
        self.logger.info(json.dumps({
            "event": "recognition_request",
            "session_id": session_id,
            "audio_length": audio_length,
            "timestamp": time.time()
        }))

    def log_recognition_result(self, session_id: str, text_length: int, confidence: float):
        self.logger.info(json.dumps({
            "event": "recognition_result",
            "session_id": session_id,
            "text_length": text_length,
            "confidence": confidence,
            "timestamp": time.time()
        }))
```

### 3. 健康检查接口
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_connections": len(connection_manager.active_connections),
        "queue_size": connection_limiter.get_queue_size(),
        "memory_usage": psutil.virtual_memory().percent,
        "cpu_usage": psutil.cpu_percent()
    }
```

## 部署架构设计

### 1. 本地开发环境
```
项目目录/
├── backend/          # 后端服务
│   ├── app/         # 应用代码
│   ├── requirements.txt
│   └── config/      # 配置文件
├── frontend/        # 前端界面
│   ├── index.html
│   ├── css/
│   └── js/
├── models/          # FunASR模型文件
├── logs/           # 日志文件
└── scripts/        # 启动脚本
```

### 2. 服务启动流程
```bash
#!/bin/bash
# start_service.sh

# 检查Python环境
python --version

# 安装依赖
pip install -r backend/requirements.txt

# 下载FunASR模型
python scripts/download_models.py

# 启动后端服务
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# 启动前端服务（可选）
cd ../frontend
python -m http.server 3000 &

echo "服务已启动"
echo "后端API: http://localhost:8000"
echo "前端界面: http://localhost:3000"
echo "WebSocket: ws://localhost:8000/ws"
```

### 3. 配置管理
```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    max_connections: int = 2

    # FunASR配置
    model_path: str = "./models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_model_path: str = "./models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    punc_model_path: str = "./models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"

    # 音频配置
    sample_rate: int = 16000
    audio_chunk_size: int = 1024
    max_audio_length: int = 30  # 秒

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    class Config:
        env_file = ".env"

settings = Settings()
```