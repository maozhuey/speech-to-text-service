# Design: 流式模型支持和模型选择

## Context

当前服务使用离线模型（paraformer-zh-16k）进行语音识别，延迟约5-10秒。FunASR 提供了流式模型（paraformer-zh-streaming），可将延迟降低到 < 800ms，大幅提升实时性。

**约束条件**：
- 硬件：M2 Pro (16GB RAM)
- 当前单模型（离线）占用约 1-2GB 内存
- 流式模型预计占用 2-3GB 内存
- 同时加载两个模型可能导致内存不足

**利益相关者**：
- 需要低延迟实时识别的用户（语音输入、实时字幕）
- 需要高精度离线识别的用户（会议记录、文档转录）
- 系统管理员（需要管理模型资源）

## Goals / Non-Goals

**Goals**:
1. 支持流式模型识别，降低延迟到 < 800ms
2. 允许客户端在连接时选择使用哪个模型
3. 保持向后兼容（默认使用离线模型）
4. 实现合理的模型加载策略，避免内存溢出

**Non-Goals**:
1. 不实现运行时动态模型切换（WebSocket 连接建立后不能切换模型）
2. 不支持同时使用多个模型进行识别
3. 不实现模型的自动下载和更新

## Decisions

### Decision 1: 模型加载策略

**选择：按需加载 + LRU 缓存**

每个模型按需加载，使用 LRU（Least Recently Used）缓存策略：
- 最多同时加载 2 个模型
- 当加载第 3 个模型时，卸载最久未使用的模型
- 默认预加载离线模型（向后兼容）

**原因**：
- 平衡了内存使用和响应速度
- 常用模型保持在内存中，避免频繁加载
- 16GB RAM 可以支持 2 个模型同时存在

**备选方案**：
1. **全部预加载**：可能导致内存不足（2-3GB × 2 = 4-6GB，加上其他开销可能超出）
2. **每次加载**：响应慢，模型加载需要时间
3. **单例模式**：只能使用一个模型，灵活性差

### Decision 2: 模型配置方式

**选择：配置文件定义可用模型，运行时可选择**

在 `config.py` 中定义模型配置：
```python
models_config = {
    "offline": {
        "name": "paraformer-zh-16k",
        "path": "/path/to/offline/model",
        "type": "offline",
        "description": "离线模型，高精度，延迟5-10秒"
    },
    "streaming": {
        "name": "paraformer-zh-streaming",
        "path": "/path/to/streaming/model",
        "type": "streaming",
        "description": "流式模型，低延迟，延迟<800ms"
    }
}
default_model = "offline"
```

**原因**：
- 配置清晰，易于维护
- 支持扩展更多模型
- 可以通过环境变量覆盖

### Decision 3: WebSocket 参数设计

**选择：查询参数 `model`**

连接示例：
```
ws://localhost:8002/ws?model=streaming
ws://localhost:8002/ws?model=offline
ws://localhost:8002/ws  // 默认使用 offline
```

**原因**：
- 符合 RESTful 风格
- 易于实现和使用
- 向后兼容（无参数时使用默认模型）

**错误处理**：
- 无效的模型名称：返回错误并关闭连接
- 模型加载失败：返回错误并关闭连接

### Decision 4: FunASRService 架构

**选择：模型管理器 + 识别器分离**

```python
class ModelManager:
    """管理模型的加载、卸载和缓存"""
    def __init__(self, max_cached_models=2):
        self.max_cached_models = max_cached_models
        self.loaded_models = OrderedDict()  # LRU 缓存

    def get_model(self, model_name):
        """获取模型，按需加载"""
        if model_name in self.loaded_models:
            # 更新 LRU 顺序
            self.loaded_models.move_to_end(model_name)
            return self.loaded_models[model_name]

        # 加载新模型
        model = self._load_model(model_name)

        # 检查缓存限制
        if len(self.loaded_models) >= self.max_cached_models:
            oldest = self.loaded_models.popitem(last=False)[0]
            self._unload_model(oldest)

        self.loaded_models[model_name] = model
        return model
```

**原因**：
- 单一职责原则
- 易于测试和维护
- 支持扩展更多模型

## Data Model

### 模型配置结构
```python
@dataclass
class ModelConfig:
    name: str           # 模型名称（offline, streaming）
    display_name: str   # 显示名称
    path: str           # 模型路径
    type: str           # 模型类型（offline, streaming）
    description: str    # 描述
    enabled: bool       # 是否启用
```

### WebSocket 连接参数
```python
@dataclass
class ConnectionParams:
    token: Optional[str] = None    # 认证令牌（可选）
    model: str = "offline"         # 模型名称（默认离线）
```

## API Changes

### WebSocket 连接
**新增参数**：
- `model` (string, 可选): 模型名称，默认 "offline"

**响应**：
- 连接成功：正常 WebSocket 握手
- 模型无效：关闭连接，code 4002, reason "Invalid model: {name}"
- 模型加载失败：关闭连接，code 4003, reason "Failed to load model: {name}"

### 模型列表 API（新增）
```
GET /api/v1/models
```
**响应**：
```json
{
  "success": true,
  "default": "offline",
  "models": [
    {
      "name": "offline",
      "display_name": "离线模型（高精度）",
      "type": "offline",
      "description": "适合会议记录、文档转录",
      "enabled": true
    },
    {
      "name": "streaming",
      "display_name": "流式模型（低延迟）",
      "type": "streaming",
      "description": "适合语音输入、实时字幕",
      "enabled": false
    }
  ]
}
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| 内存溢出 | 高 | 实现 LRU 缓存，限制同时加载的模型数 |
| 模型加载时间 | 中 | 预加载默认模型，缓存常用模型 |
| 并发冲突 | 中 | 使用线程锁保护模型加载/卸载 |
| 配置错误 | 低 | 启动时验证模型路径，提供清晰的错误信息 |

**Trade-offs**:
1. **延迟 vs 内存**：流式模型延迟低但内存占用大
2. **精度 vs 速度**：离线模型精度高但速度慢
3. **灵活性 vs 复杂度**：支持多模型增加了代码复杂度

## Migration Plan

### 阶段 1：准备工作
1. 下载流式模型到 `models/` 目录
2. 更新配置文件添加模型配置
3. 编写模型管理单元测试

### 阶段 2：核心实现
1. 实现 ModelManager 类
2. 修改 FunASRService 使用 ModelManager
3. 更新 WebSocket 端点处理 model 参数

### 阶段 3：前端和文档
1. 更新前端添加模型选择
2. 编写 API 文档
3. 更新 README

### 阶段 4：测试和部署
1. 完整测试流程
2. 内存压力测试
3. 灰度发布

### 回滚计划
- 保留原离线模型逻辑，可通过配置禁用新功能
- 如果出现问题，可回退到旧版本

## Open Questions

1. **流式模型下载**：流式模型的官方下载地址和模型文件结构？
   - 需要查阅 FunASR 官方文档

2. **流式模型 API**：流式模型的调用方式和离线模型是否一致？
   - 需要查阅 FunASR API 文档

3. **并发限制**：当前最大支持 2 个并发连接，加载流式模型后是否需要调整？
   - 需要进行压力测试

4. **模型精度对比**：流式模型的识别准确率相比离线模型如何？
   - 需要进行对比测试
