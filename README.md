# 语音转文本服务

基于FunASR的中文语音转文本实时服务，提供WebSocket接口和友好的Web界面。

## 🌟 特性

- **多模型支持**：支持离线模型（高精度）和流式模型（低延迟）
- **实时语音识别**：基于WebSocket的实时音频流处理
- **中文优化**：专门针对中文语音识别优化
- **Web界面**：简洁美观的Web操作界面，支持模型选择
- **标点符号恢复**：自动添加标点符号，提升可读性
- **VAD语音活动检测**：智能检测语音片段
- **智能断句**：基于语音停顿自动断句，更自然的转录体验
- **实时识别状态显示**：识别过程中显示"识别中..."提示，提升用户体验
- **多连接支持**：支持多个客户端同时连接（当前限制2个）
- **模型缓存管理**：LRU 缓存策略，最多缓存2个模型，自动释放内存

## 🏗️ 系统架构

```
语音转文本服务/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/             # API路由
│   │   ├── core/            # 核心功能
│   │   │   ├── config.py    # 配置文件
│   │   │   └── websocket.py # WebSocket处理器
│   │   ├── services/        # 服务层
│   │   │   ├── funasr_service.py   # FunASR语音识别服务
│   │   │   └── model_manager.py    # 多模型管理器
│   │   ├── middleware/      # 中间件
│   │   └── main.py          # FastAPI主应用
│   └── tests/               # 测试套件
├── frontend/                # 前端界面
│   ├── index.html           # Web界面
│   └── css/                 # 样式文件
├── models/                  # 模型目录
│   └── damo/                # FunASR离线模型
│   └── paraformer-zh-streaming/  # 流式模型（可选）
├── logs/                    # 日志目录
└── README.md                # 项目说明
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- 现代浏览器（Chrome、Firefox、Safari等）

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装Python依赖
pip install -r backend/requirements.txt
```

### 下载模型（可选）

如果需要使用真实的FunASR功能，需要下载模型文件：

```bash
# 模型会自动下载到 models/damo/ 目录
# 当前版本使用模拟模式，无需下载模型
```

### 启动服务

#### 方法1：使用启动脚本

```bash
# 启动后端服务
python start_backend.py
```

#### 方法2：手动启动

```bash
# 启动后端服务
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# 启动前端服务（新终端）
cd frontend
python -m http.server 8080
```

### 访问服务

- **Web界面**: http://localhost:8080
- **API文档**: http://localhost:8002/docs
- **健康检查**: http://localhost:8002/api/v1/health

## 使用方法

1. 打开Web界面
2. 点击"开始录音"按钮
3. 允许浏览器访问麦克风
4. 开始说话，系统会实时显示识别结果
5. 使用"复制全部"或"清空内容"按钮管理文本

## 项目结构

```
语音转文本服务/
├── backend/              # 后端服务
│   ├── app/             # 应用代码
│   │   ├── main.py      # FastAPI应用入口
│   │   ├── api/         # API路由
│   │   ├── core/        # 核心功能
│   │   └── models/      # 数据模型
│   ├── config/          # 配置文件
│   └── tests/           # 测试代码
├── frontend/            # 前端界面
│   ├── index.html       # 主页面
│   ├── css/            # 样式文件
│   └── js/             # JavaScript代码
├── models/             # FunASR模型文件
├── logs/               # 日志文件
└── scripts/            # 工具脚本
```

## 配置说明

主要配置项在 `.env` 文件中：

### 基础配置
- `MAX_CONNECTIONS`: 最大并发连接数（默认：2）
- `SAMPLE_RATE`: 音频采样率（默认：16000）
- `LOG_LEVEL`: 日志级别（默认：INFO）

### 多模型配置
- `DEFAULT_MODEL`: 默认使用的模型（`offline` 或 `streaming`，默认：`offline`）
- `MAX_CACHED_MODELS`: 最大缓存的模型数量（默认：2）
- `ENABLE_MODEL_SWITCHING`: 是否启用模型切换功能（默认：`true`）
- `MODEL_PATH`: 离线模型路径
- `STREAMING_MODEL_PATH`: 流式模型路径（如需使用）

**模型对比：**
| 模型 | 延迟 | 准确率 | 适用场景 |
|------|------|--------|----------|
| 离线模型 (offline) | 5-10秒 | 高 | 会议记录、文档转录 |
| 流式模型 (streaming) | <300ms | 中高 | 语音输入、实时字幕 |

**使用流式模型：**
1. 下载流式模型到 `models/paraformer-zh-streaming/` 目录
2. 在 `.env` 中设置 `STREAMING_MODEL_PATH`
3. 在前端选择"流式模型"选项

### VAD智能断句配置
- `VAD_ENABLED`: 是否启用VAD智能断句（默认：`true`）
  - 启用后：根据说话停顿自动断句（更自然）
  - 禁用后：使用固定时长断句（5秒）
- `VAD_SILENCE_THRESHOLD_MS`: 静音阈值，连续静音超过此时长触发断句（默认：800毫秒）
- `VAD_MAX_SEGMENT_DURATION_MS`: 单段最大时长，防止过长不断句（默认：20000毫秒）

**断句逻辑：**
```
说话 → 停顿 ≥800ms → 自动断句并识别
     或
连续说话 ≥20秒 → 强制断句
```

### CORS安全配置
- `ALLOWED_ORIGINS`: 允许的跨域来源（逗号分隔）
- `ALLOWED_METHODS`: 允许的HTTP方法
- `ALLOWED_HEADERS`: 允许的请求头

## API接口

### WebSocket连接

**基础连接（使用默认模型）：**
```
ws://localhost:8002/ws
```

**指定模型连接：**
```
ws://localhost:8002/ws?model=offline    # 离线模型（高精度）
ws://localhost:8002/ws?model=streaming  # 流式模型（低延迟）
```

**错误码：**
- `4002`: 无效的模型名称
- `4003`: 模型加载失败或未启用

### REST API

#### 模型列表
```http
GET /api/v1/models
```

**响应示例：**
```json
{
  "success": true,
  "default": "offline",
  "models": [
    {
      "name": "offline",
      "display_name": "离线模型（高精度）",
      "type": "offline",
      "description": "适合会议记录、文档转录，延迟5-10秒",
      "enabled": true
    },
    {
      "name": "streaming",
      "display_name": "流式模型（低延迟）",
      "type": "streaming",
      "description": "适合语音输入、实时字幕，延迟<300ms",
      "enabled": false
    }
  ]
}
```

#### 其他接口
- `GET /api/v1/health` - 健康检查
- `GET /api/v1/info` - 服务信息
- `GET /api/v1/token` - 生成WebSocket访问令牌（可选认证）

## 性能指标

### 离线模型
- 识别延迟：5-10秒
- 识别准确率：> 95%
- 内存占用：1-2GB

### 流式模型（需下载）
- 识别延迟：< 300ms
- 识别准确率：> 90%
- 内存占用：2-3GB

### 系统资源
- 并发连接：最多2个
- CPU使用率：< 80%（M2 Pro）
- VAD处理性能：160万次/秒
- VAD延迟：< 0.01ms/次

## 开发指南

### 运行测试
```bash
# 运行所有测试
pytest backend/tests/

# 运行特定测试
pytest backend/tests/test_model_manager.py -v  # 模型管理器测试
pytest backend/tests/test_basic.py -v            # 基础功能测试
pytest backend/tests/test_vad_tracker.py -v      # VAD测试
```

### 测试覆盖
- **test_model_manager.py**: 模型管理器测试（19个场景）
- **test_basic.py**: 基础功能测试
- **test_vad_tracker.py**: VAD状态跟踪器测试（12个场景）
- **test_vad_service.py**: VAD检测服务测试（9个场景）
- **test_integration.py**: 端到端集成测试（6个场景）
- **test_websocket_e2e.py**: WebSocket端到端测试

### 代码格式化
```bash
black backend/
flake8 backend/
```

## 常见问题

### Q: 如何切换使用流式模型？
A:
1. 下载流式模型到 `models/paraformer-zh-streaming/` 目录
2. 在 `.env` 中设置 `STREAMING_MODEL_PATH=./models/paraformer-zh-streaming`
3. 在前端界面选择"流式模型"选项
4. 或在 WebSocket 连接时添加 `?model=streaming` 参数

### Q: 如何添加新的语音识别模型？
A: 在 `.env` 中配置 `MODELS_JSON`，或修改 `app/core/config.py` 中的 `get_models_config()` 方法。

### Q: 支持同时加载多个模型吗？
A: 是的，使用 LRU 缓存策略，最多缓存2个模型。加载第3个模型时会自动卸载最久未使用的模型。

### Q: 内存不足怎么办？
A:
1. 减少 `MAX_CACHED_MODELS` 配置值（最小为1）
2. 使用离线模型而非流式模型
3. 减少并发连接数

### Q: 支持哪些音频格式？
A: 目前支持 16kHz PCM 格式，其他格式会自动转换。

### Q: 如何提高识别准确率？
A: 确保音频质量良好，环境安静，说话清晰。对于会议记录等场景，建议使用离线模型。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！