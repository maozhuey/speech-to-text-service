# FunASR集成设计文档

## 架构设计

### 1. FunASR服务层设计

创建新的服务层 `backend/app/services/funasr_service.py`，封装FunASR的所有功能：

```python
class FunASRService:
    """FunASR语音识别服务"""

    def __init__(self):
        self.speech_model = None
        self.vad_model = None
        self.punc_model = None

    async def initialize(self):
        """异步初始化所有模型"""

    async def recognize_speech(self, audio_data: bytes) -> RecognitionResult:
        """执行语音识别"""

    async def detect_voice_activity(self, audio_data: bytes) -> bool:
        """检测语音活动"""

    async def add_punctuation(self, text: str) -> str:
        """添加标点符号"""
```

### 2. WebSocket处理器修改

修改 `backend/app/core/websocket.py` 的 `process_audio` 方法：

- 移除模拟实现
- 集成FunASRService
- 实现实时音频流处理
- 添加错误处理和重试机制

### 3. 模型管理设计

增强 `scripts/download_models.py`：
- 添加进度显示
- 支持断点续传
- 添加模型完整性校验
- 创建模型版本管理

## 实现细节

### 1. 音频处理流程

```
音频流输入 → VAD检测 → 语音分段 → FunASR识别 → 标点恢复 → 结果返回
```

### 2. 并发处理策略

- 使用异步处理保证响应性
- 每个连接维护独立的音频缓冲区
- 实现连接池管理，最大支持2个并发

### 3. 错误处理机制

- 模型加载失败降级处理
- 音频识别超时处理
- WebSocket异常重连
- 资源清理机制

## 性能优化

### 1. 模型加载优化

- 使用懒加载，按需加载模型
- 实现模型缓存机制
- 支持模型热更新

### 2. 音频处理优化

- 使用音频流式处理
- 实现音频缓冲区管理
- 优化音频格式转换

### 3. 内存管理

- 限制音频缓冲区大小
- 定期清理过期数据
- 监控内存使用情况

## 安全考虑

1. **输入验证**：验证音频数据格式和大小
2. **资源限制**：限制并发连接数和请求频率
3. **错误隔离**：单个连接的错误不影响其他连接
4. **日志记录**：记录关键操作和错误信息

## 测试策略

1. **单元测试**：测试FunASR服务各个方法
2. **集成测试**：测试WebSocket端到端流程
3. **性能测试**：验证延迟和并发能力
4. **错误测试**：模拟各种异常情况

## 部署注意事项

1. 确保环境有足够内存加载模型（建议8GB+）
2. 配置适当的超时参数
3. 设置日志级别和输出位置
4. 监控系统资源使用情况