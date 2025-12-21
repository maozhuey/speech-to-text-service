# 语音转文本基础服务

基于FunASR的中文语音转文本服务，支持实时语音识别、说话人分离、智能标点和时间戳功能。

## 功能特性

- 🎤 **实时语音识别**：低延迟的中文语音转文本
- 👥 **说话人分离**：自动识别和标注不同说话人
- 📝 **智能标点**：自动添加中文标点符号
- ⏰ **时间戳支持**：精确记录每句话的时间信息
- 🔗 **WebSocket通信**：实时双向数据传输
- 🚀 **性能优化**：针对M2 Pro设备优化，支持2个并发连接

## 快速开始

### 环境要求

- Python 3.9+
- M2 Pro (16GB RAM) MacBook Pro（推荐）
- 支持的浏览器：Chrome 80+, Firefox 75+, Safari 13+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd 语音转文本服务
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境**
```bash
cp .env.example .env
# 根据需要修改 .env 文件中的配置
```

5. **启动服务**
```bash
# 启动后端服务
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 在另一个终端启动前端服务（可选）
cd frontend
python -m http.server 3000
```

6. **访问界面**
- Web界面：http://localhost:3000
- API文档：http://localhost:8000/docs
- WebSocket：ws://localhost:8000/ws

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

- `MAX_CONNECTIONS`: 最大并发连接数（默认：2）
- `SAMPLE_RATE`: 音频采样率（默认：16000）
- `LOG_LEVEL`: 日志级别（默认：INFO）

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