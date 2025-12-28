# 设计：标点符号实时显示

## 架构概述

在现有WebSocket实时通信架构基础上，增加流式识别和中间结果显示能力。

## 方案选择

### 方案A：后端流式识别（推荐）

**流程：**
```
用户说话 → 音频流 → VAD检测 → FunASR流式识别
                              ↓
                         返回中间结果
                              ↓
                    前端实时显示（灰色）
                              ↓
                         最终结果（黑色）
```

**优点：**
- 真正的实时反馈
- 用户体验最好
- 符合用户预期

**缺点：**
- 依赖FunASR流式API
- 增加后端复杂度

**实现条件：**
- 需验证FunASR是否支持流式识别

### 方案B：前端模拟实时（备选）

**流程：**
```
用户说话 → 音频累积 → VAD断句 → FunASR识别 → 返回结果
                              ↓
                      前端显示"识别中..."
                              ↓
                         最终结果（黑色）
```

**优点：**
- 不依赖流式API
- 实现简单
- 兼容现有架构

**缺点：**
- 不是真正的实时
- 用户体验较差

### 方案C：混合方案

**流程：**
- 优先尝试流式识别
- 降级到方案B

## 技术设计

### 前端设计

#### 1. 中间结果显示区域

```javascript
updateInterimText(text) {
    // 查找或创建中间结果显示元素
    let interimElement = this.textDisplay.querySelector('.interim-text');

    if (!interimElement) {
        interimElement = document.createElement('div');
        interimElement.className = 'interim-text mb-2 text-gray-400 italic';
        this.textDisplay.appendChild(interimElement);
    }

    interimElement.textContent = text;
    this.scrollToBottom();
}

addFinalText(text, speaker) {
    // 清除中间结果
    const interimElement = this.textDisplay.querySelector('.interim-text');
    if (interimElement) {
        interimElement.remove();
    }

    // 添加最终结果（原有逻辑）
    // ...
}
```

#### 2. 样式设计

```css
.interim-text {
    color: #9CA3AF;  /* 灰色 */
    font-style: italic;
    opacity: 0.8;
    transition: opacity 0.2s;
}

.final-text {
    color: #FFFFFF;  /* 白色 */
    opacity: 1;
    transition: opacity 0.3s;
}
```

### 后端设计

#### 1. 流式识别接口（如果FunASR支持）

```python
async def recognize_speech_streaming(self, audio_data: bytes):
    """流式识别，返回中间结果"""
    # TODO: 验证FunASR流式API
    for partial_result in funasr_streaming_recognize(audio_data):
        yield {
            "success": True,
            "text": partial_result["text"],
            "is_final": False,
            "timestamp": time.time()
        }

    # 最终结果
    yield {
        "success": True,
        "text": final_text_with_punctuation,
        "is_final": True,
        "timestamp": time.time()
    }
```

#### 2. 消息格式

```json
{
    "type": "recognition_result",
    "text": "今天天气",
    "is_final": false,
    "confidence": 0.8
}
```

```json
{
    "type": "recognition_result",
    "text": "今天天气怎么样？",
    "is_final": true,
    "speaker": "speaker_1",
    "confidence": 0.95
}
```

### WebSocket设计

#### 消息类型

| 类型 | 方向 | 说明 |
|------|------|------|
| `recognition_result` | Server→Client | 识别结果（is_final区分中间/最终） |
| `processing` | Server→Client | 处理中提示 |

## 数据流

```
┌─────────┐     ┌──────────┐     ┌─────────┐
│ 前端录音 │ ──→ │ WebSocket│ ──→ │ VAD检测 │
└─────────┘     └──────────┘     └─────────┘
                                    │
                                    ↓
                              ┌─────────┐
                              │FunASR   │
                              │流式识别 │
                              └─────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
              ┌──────────┐                    ┌──────────┐
              │中间结果   │                    │最终结果   │
              │is_final: │                    │is_final: │
              │false     │                    │true      │
              └──────────┘                    └──────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ↓
                              ┌──────────┐
                              │前端显示   │
                              │灰色→黑色 │
                              └──────────┘
```

## 性能考虑

1. **实时延迟**：目标 < 500ms
2. **更新频率**：每200-300ms一次中间结果
3. **DOM更新**：使用局部更新，避免全量重渲染
4. **网络开销**：增加中间结果消息，但每条消息很小

## 兼容性

- 现有WebSocket协议兼容
- 消息格式向后兼容（仅添加 `is_final` 字段）
- 降级方案：不支持流式时回退到现有模式

## 测试策略

1. **单元测试**：中间结果显示逻辑
2. **集成测试**：流式识别端到端
3. **性能测试**：实时延迟、DOM更新性能
4. **兼容性测试**：降级模式
