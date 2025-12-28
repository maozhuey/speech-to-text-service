# Change: 添加流式模型支持和模型选择功能

## Why

当前服务使用离线模型（paraformer-zh-16k）进行语音识别，存在以下问题：
- **延迟较高**：离线模型需要收集完整音频片段后才能识别，延迟约5-10秒
- **实时性不足**：不适合需要快速反馈的场景（如语音输入法）
- **无模型选择**：客户端无法根据使用场景选择合适的模型

FunASR 框架提供了流式模型（paraformer-zh-streaming），可以实现：
- **低延迟**：流式识别延迟 < 800ms
- **实时反馈**：边说边识别，提升用户体验
- **灵活配置**：支持离线/流式模型切换

## What Changes

- 下载并配置 FunASR 流式模型（paraformer-zh-streaming）
- 在 FunASRService 中添加模型初始化逻辑，支持同时加载多个模型
- 在 WebSocket 连接时支持通过参数指定使用哪个模型（model 参数）
- 在前端添加模型选择 UI 控件
- 修改配置文件以支持多个模型路径配置
- **BREAKING**：WebSocket 连接参数变化（新增 model 参数，可选）
- **BREAKING**：配置文件新增模型配置项

## Impact

- Affected specs:
  - `speech-recognition` - 语音识别核心服务
  - `websocket-api` - WebSocket API 接口
  - `configuration` - 配置管理

- Affected code:
  - `app/services/funasr_service.py` - 模型初始化和识别逻辑
  - `app/core/config.py` - 添加模型配置项
  - `app/core/websocket.py` - 处理模型参数
  - `app/main.py` - WebSocket 端点参数
  - `frontend/index.html` - 添加模型选择控件
  - `scripts/download_model.py` - 支持下载流式模型

- Performance impact:
  - 流式模型内存占用约 2-3GB（离线模型约 1-2GB）
  - 同时加载两个模型可能超出 M2 Pro 16GB RAM 限制
  - 需要实现按需加载或单模型切换机制

- Migration:
  - 现有客户端无需修改（默认使用离线模型）
  - 新客户端可通过 model=streaming 参数使用流式模型
