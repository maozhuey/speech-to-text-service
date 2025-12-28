# VAD智能断句技术设计

## 架构概述

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   前端      │     │  WebSocket   │     │  FunASR     │
│  录音采集   │ ──> │   处理器     │ ──> │  ASR服务    │
└─────────────┘     └──────────────┘     └─────────────┘
                          │
                          ▼
                    ┌──────────────┐
                    │  VAD检测器   │
                    │  (新增模块)  │
                    └──────────────┘
```

## 核心组件

### 1. VAD状态跟踪器

```python
class VADStateTracker:
    """跟踪单个WebSocket连接的VAD状态"""

    def __init__(self, silence_threshold_ms: int = 800):
        self.silence_threshold_ms = silence_threshold_ms
        self.consecutive_silence_ms = 0
        self.last_segment_time = 0
        self.total_segment_duration_ms = 0

    def process_audio_chunk(self, has_speech: bool, chunk_duration_ms: float) -> bool:
        """
        处理音频块，返回是否应该触发断句

        Args:
            has_speech: VAD检测结果
            chunk_duration_ms: 当前音频块时长

        Returns:
            bool: 是否应该触发断句
        """
        if has_speech:
            self.consecutive_silence_ms = 0
            self.total_segment_duration_ms += chunk_duration_ms
            # 检查是否超过最大时长
            return self.total_segment_duration_ms >= self.max_duration_ms
        else:
            self.consecutive_silence_ms += chunk_duration_ms
            # 检查是否达到静音阈值
            return self.consecutive_silence_ms >= self.silence_threshold_ms
```

### 2. 集成点

#### 位置：`backend/app/core/websocket.py`

```python
async def process_audio(self, websocket: WebSocket, audio_data: bytes):
    """处理音频数据（集成VAD）"""

    # 1. 添加到缓冲区
    self.audio_segments[websocket].append(audio_data)

    # 2. VAD检测（新增）
    vad_result = await self._detect_voice_activity(audio_data)
    has_speech = vad_result.get('has_speech', True)

    # 3. 更新VAD状态（新增）
    should_segment = self.vad_trackers[websocket].process_audio_chunk(
        has_speech,
        chunk_duration_ms=len(audio_data) / 16  # 16kHz => ms转换
    )

    # 4. 触发断句判断
    if should_segment and self.audio_segments[websocket]:
        await self._recognize_audio_segment(websocket, self.audio_segments[websocket][:])
        self.audio_segments[websocket] = []
        self.vad_trackers[websocket].reset()
```

### 3. 配置管理

#### 位置：`backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # VAD断句配置
    VAD_SILENCE_THRESHOLD_MS: int = Field(default=800, description="静音阈值（毫秒）")
    VAD_MAX_SEGMENT_DURATION_MS: int = Field(default=20000, description="单段最大时长（毫秒）")
    VAD_ENABLED: bool = Field(default=True, description="是否启用VAD断句")
```

## 数据流

### 正常断句流程

```
时间轴: ───────────────────────────────────────────────────────>
音频:   [说话] [说话] [静音] [静音] [静音] [说话]
VAD:     语音   语音   静音   静音   静音   语音
状态:    ───────────────> 累积静音 ────────> 触发断句!
```

### 超时断句流程

```
时间轴: ──────────────────────────────────────────────────────>
音频:   [说话] ... [说话] ... [说话] ... (持续20秒)
时长:   ────────────────────────────────> 达到最大时长
状态:    ────────────────────────────────> 强制断句!
```

## 性能考虑

### VAD调用频率
- 每个音频块（约256ms）调用一次
- 使用异步任务，不阻塞主流程
- VAD模型已经加载在内存中，调用开销小

### 内存使用
- 每个连接维护一个VAD状态跟踪器（约100字节）
- 音频缓冲区最大20秒（约640KB）
- 总体内存增加可忽略

### CPU使用
- VAD检测增加约5-10% CPU使用
- FunASR VAD模型针对CPU优化
- 可通过配置禁用VAD

## 错误处理

### VAD检测失败
- **降级策略**：VAD失败时回退到固定时长断句
- **日志记录**：记录VAD失败原因
- **状态标记**：在响应中标记使用的是VAD还是固定时长

### 异常情况
- **空音频**：直接跳过处理
- **格式错误**：返回错误给客户端
- **连接断开**：清理所有状态

## 测试策略

### 单元测试
```python
def test_vad_state_tracker():
    tracker = VADStateTracker(silence_threshold_ms=800)

    # 模拟3个音频块：语音、静音、静音
    assert not tracker.process_audio_chunk(True, 400)   # 400ms语音
    assert not tracker.process_audio_chunk(False, 400)  # 400ms静音，总计400ms
    assert tracker.process_audio_chunk(False, 500)      # 500ms静音，总计900ms → 触发
```

### 集成测试
```python
async def test_vad_integration():
    # 发送包含停顿的音频
    await send_audio_with_silence(websocket, speech_1s, silence_1s)

    # 验证在停顿后触发断句
    assert await receive_recognition_result(websocket)
```

## 迁移策略

### 阶段1：功能开发
- 实现VAD状态跟踪器
- 集成到WebSocket处理器
- 添加配置项

### 阶段2：测试验证
- 单元测试覆盖
- 集成测试验证
- 性能基准测试

### 阶段3：灰度发布
- 默认禁用VAD（`VAD_ENABLED=false`）
- 逐步启用并观察效果
- 收集用户反馈

### 阶段4：全量发布
- 设置为默认启用
- 监控性能指标
- 根据反馈优化参数
