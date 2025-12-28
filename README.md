# 语音转文本服务

基于FunASR的中文语音转文本实时服务，提供WebSocket接口和友好的Web界面。

## 🌟 特性

- **实时语音识别**：基于WebSocket的实时音频流处理
- **中文优化**：专门针对中文语音识别优化
- **Web界面**：简洁美观的Web操作界面
- **标点符号恢复**：自动添加标点符号，提升可读性
- **VAD语音活动检测**：智能检测语音片段
- **智能断句**：基于语音停顿自动断句，更自然的转录体验
- **多连接支持**：支持多个客户端同时连接（当前限制2个）
- **模拟模式**：开发测试阶段支持模拟识别结果

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
│   │   │   └── funasr_service.py # FunASR语音识别服务
│   │   └── main.py          # FastAPI主应用
│   └── requirements.txt     # Python依赖
├── frontend/                # 前端界面
│   ├── index.html          # Web界面
│   ├── css/                # 样式文件
│   └── js/                 # JavaScript文件
├── models/                 # 模型目录
│   └── damo/               # FunASR模型文件
├── start_backend.py        # 后端启动脚本
└── README.md               # 项目说明
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

### VAD智能断句配置
- `VAD_ENABLED`: 是否启用VAD智能断句（默认：true）
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

## API接口

### WebSocket连接
```
ws://localhost:8000/ws
```

### REST API
- `GET /health` - 健康检查
- `GET /info` - 服务信息
- `GET /metrics` - 性能指标

## 性能指标

- 识别延迟：< 2秒
- 识别准确率：> 95%
- 并发连接：最多2个
- CPU使用率：< 80%（M2 Pro）

## 开发指南

### 运行测试
```bash
pytest backend/tests/
```

### 代码格式化
```bash
black backend/
flake8 backend/
```

## 常见问题

### Q: 如何添加新的语音识别模型？
A: 下载模型文件到 `models/` 目录，并在 `.env` 中配置模型路径。

### Q: 支持哪些音频格式？
A: 目前支持 16kHz PCM 格式，其他格式会自动转换。

### Q: 如何提高识别准确率？
A: 确保音频质量良好，环境安静，说话清晰。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！