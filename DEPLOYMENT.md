# 部署指南

本文档详细说明了如何在不同环境中部署语音转文本服务。

## 📋 部署清单

在部署前，请确认以下条件：

- [ ] Python 3.9+ 运行环境
- [ ] 足够的计算资源（推荐 8GB+ RAM）
- [ ] 网络访问权限（用于下载模型）
- [ ] 防火墙配置（开放所需端口）

## 🔧 本地部署

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd 语音转文本服务

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r backend/requirements.txt
```

### 2. 配置服务

编辑 `backend/app/core/config.py` 中的配置：

```python
class Settings:
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8002

    # FunASR配置
    model_dir: str = "models/damo"

    # 性能配置
    max_connections: int = 2
    connection_timeout: int = 300
```

### 3. 启动服务

```bash
# 方法1：使用启动脚本
python start_backend.py

# 方法2：使用uvicorn
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002

# 启动前端（可选）
cd frontend
python -m http.server 8080
```

## 🐳 Docker部署

### 1. 创建Dockerfile

```dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY start_backend.py .

# 安装Python依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

# 创建模型目录
RUN mkdir -p models/damo

# 暴露端口
EXPOSE 8002 8080

# 启动命令
CMD ["python", "start_backend.py"]
```

### 2. 构建和运行

```bash
# 构建镜像
docker build -t speech-to-text .

# 运行容器
docker run -d \
  --name speech-to-text \
  -p 8002:8002 \
  -p 8080:8080 \
  -v $(pwd)/models:/app/models \
  speech-to-text
```

## 🚀 生产环境部署

### 1. 使用Gunicorn

```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务
cd backend
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8002 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --daemon
```

### 2. 使用Nginx反向代理

创建Nginx配置文件 `/etc/nginx/sites-available/speech-to-text`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend;
        try_files $uri $uri/ =404;
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket代理
    location /ws {
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/speech-to-text /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. 使用Systemd服务

创建服务文件 `/etc/systemd/system/speech-to-text.service`：

```ini
[Unit]
Description=Speech-to-Text Service
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/speech-to-text
Environment=PATH=/opt/speech-to-text/venv/bin
ExecStart=/opt/speech-to-text/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable speech-to-text
sudo systemctl start speech-to-text
```

## 🔍 监控和日志

### 1. 日志配置

```python
# 在 config.py 中配置日志
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "file": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "": {
            "handlers": ["file"],
            "level": "INFO",
        },
    },
}
```

### 2. 健康检查

```bash
# 检查服务状态
curl http://localhost:8002/api/v1/health

# 检查服务信息
curl http://localhost:8002/api/v1/info
```

### 3. 性能监控

使用Prometheus和Grafana进行监控：

```python
# 添加Prometheus指标
from prometheus_client import Counter, Histogram, start_http_server

REQUEST_COUNT = Counter('requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')

# 在API中使用
@REQUEST_LATENCY.time()
async def some_endpoint():
    REQUEST_COUNT.inc()
    # 处理逻辑
```

## 🔒 安全配置

### 1. HTTPS配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 其他配置...
}
```

### 2. 访问控制

```python
# 在main.py中添加认证中间件
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, HTTPException, status

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API密钥认证
async def verify_api_key(api_key: str = Header(...)):
    if api_key != "your-secret-key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key
```

## 📊 性能优化

### 1. 缓存配置

```python
# 使用Redis缓存
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# 缓存识别结果
@lru_cache(maxsize=1000)
def cached_recognition(audio_hash):
    # 识别逻辑
    pass
```

### 2. 连接池配置

```python
# WebSocket连接池优化
class ConnectionManager:
    def __init__(self, max_connections: int = 10):  # 增加连接数
        self.max_connections = max_connections
        # 其他配置...
```

## 🚨 故障排除

### 常见问题及解决方案

1. **模型加载失败**
   - 检查模型文件完整性
   - 确认磁盘空间充足
   - 验证文件权限

2. **内存不足**
   - 减少并发连接数
   - 增加系统内存
   - 优化模型加载

3. **WebSocket连接断开**
   - 检查网络稳定性
   - 调整超时设置
   - 实现自动重连机制

### 日志分析

```bash
# 查看错误日志
grep ERROR logs/app.log

# 监控实时日志
tail -f logs/app.log

# 分析访问模式
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c
```

## 🔄 升级指南

### 1. 备份数据

```bash
# 备份配置文件
cp -r backend/app/core/config.py config_backup.py

# 备份模型
tar -czf models_backup.tar.gz models/
```

### 2. 更新代码

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r backend/requirements.txt --upgrade
```

### 3. 迁移数据

```bash
# 如果有数据库，执行迁移
python manage.py migrate
```

### 4. 重启服务

```bash
sudo systemctl restart speech-to-text
```

## 📞 支持

如果在部署过程中遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 检查系统资源使用情况
3. 确认网络连接和防火墙设置
4. 参考项目文档或提交Issue

---

**注意**：生产环境部署建议进行充分的测试，并做好监控和备份工作。