# FunASR Web界面设计文档

## 系统架构设计

### 整体架构
```
┌─────────────────────────────────────────────────────┐
│                 index.html                         │
│  ┌─────────────────────────────────────────────┐   │
│  │              HTML Structure                │   │
│  │  ┌─────────────┐  ┌────────────────────┐   │   │
│  │  │   Header    │  │   Status Bar       │   │   │
│  │  │ (Title)     │  │ (Connection Status)│   │   │
│  │  └─────────────┘  └────────────────────┘   │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │        Text Display Area           │   │   │
│  │  │  ┌─────────────────────────────┐   │   │
│  │  │  │     Sentence Container      │   │   │
│  │  │  │  ┌─────────┐ ┌─────────────┐ │   │   │
│  │  │  │  │ Final   │ │ Interim    │ │   │   │
│  │  │  │  │ Text    │ │ Text       │ │   │   │
│  │  │  │  └─────────┘ └─────────────┘ │   │   │
│  │  │  └─────────────────────────────┘   │   │
│  │  └─────────────────────────────────────┘   │
│  │  ┌─────────────┐  ┌────────────────────┐   │   │
│  │  │   Footer    │  │   Action Buttons   │   │   │
│  │  │             │  │ (Copy/Clear)       │   │   │
│  │  └─────────────┘  └────────────────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │            JavaScript Modules              │   │
│  │  • WebSocketManager                         │   │
│  │  • TextRenderer                             │   │
│  │  • UIController                             │   │
│  │  • Utils                                    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                       │
                       │ WebSocket
                       ▼
┌─────────────────────────────────────────────────────┐
│              FunASR Service                         │
│              (ws://127.0.0.1:10095)                │
└─────────────────────────────────────────────────────┘
```

### 核心模块设计

#### 1. WebSocketManager 模块
```javascript
class WebSocketManager {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.reconnectTimer = null;
    this.onMessage = null;
    this.onStatusChange = null;
  }

  // 方法
  connect()
  disconnect()
  send(data)
  reconnect()
  getStatus()
}
```

#### 2. TextRenderer 模块
```javascript
class TextRenderer {
  constructor(container) {
    this.container = container;
    this.currentSentence = null;
    this.sentences = [];
  }

  // 方法
  addFinalText(text)
  updateInterimText(text)
  clear()
  getAllText()
  scrollToBottom()
}
```

#### 3. UIController 模块
```javascript
class UIController {
  constructor() {
    this.statusIndicator = null;
    this.connectButton = null;
    this.copyButton = null;
    this.clearButton = null;
  }

  // 方法
  updateStatus(status, message)
  initElements()
  bindEvents()
}
```

## 数据流设计

### WebSocket消息处理流程
```
WebSocket Message
       │
       ▼
  JSON Parse
       │
       ▼
  Message Validation
       │
       ├─ is_final: true ──► finalizeSentence()
       │                         │
       │                         ▼
       │                 createNewSentence()
       │
       └─ is_final: false ─► updateInterimText()
                                │
                                ▼
                        updateCurrentSentence()
```

### DOM更新策略
```
文本更新请求
       │
       ▼
  DocumentFragment 创建
       │
       ▼
  文本节点创建/更新
       │
       ▼
  批量DOM操作
       │
       ▼
  滚动位置调整
       │
       ▼
  性能优化清理
```

## UI组件详细设计

### 1. 连接状态指示器
```html
<div class="status-indicator">
  <div class="status-dot" data-status="connecting"></div>
  <span class="status-text">正在连接...</span>
</div>
```

**状态样式：**
- 连接中：黄色圆点 + 闪烁动画
- 已连接：绿色圆点 + 静态
- 已断开：红色圆点 + 显示重连按钮

### 2. 文本显示区域
```html
<div class="text-container" id="textDisplay">
  <!-- 句子容器 -->
  <div class="sentence" data-sentence-id="1">
    <span class="final-text">这是最终文本</span>
    <span class="interim-text">这是中间文本</span>
  </div>
</div>
```

### 3. 操作按钮组
```html
<div class="action-buttons">
  <button class="btn btn-primary" id="copyBtn">
    <svg>...</svg> 复制全部
  </button>
  <button class="btn btn-secondary" id="clearBtn">
    <svg>...</svg> 清空屏幕
  </button>
</div>
```

## 性能优化设计

### 1. DOM操作优化
- **DocumentFragment**：批量DOM更新
- **虚拟滚动**：大量文本时只渲染可见部分
- **事件委托**：减少事件监听器数量
- **节流/防抖**：控制频繁操作

### 2. 内存管理
- **句子数量限制**：保留最近1000句
- **清理策略**：FIFO（先进先出）删除旧句子
- **弱引用**：避免内存泄漏

### 3. 渲染优化
```javascript
// 使用requestAnimationFrame优化滚动
function smoothScrollToBottom() {
  requestAnimationFrame(() => {
    const container = textContainer;
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth'
    });
  });
}

// 批量DOM更新
function batchUpdate(updates) {
  const fragment = document.createDocumentFragment();
  updates.forEach(update => fragment.appendChild(update));
  container.appendChild(fragment);
}
```

## 错误处理设计

### 1. WebSocket错误处理
```javascript
ws.onerror = (event) => {
  console.error('WebSocket error:', event);
  updateStatus('error', '连接错误');
  showNotification('连接失败，请检查FunASR服务是否运行');
};

ws.onclose = (event) => {
  if (!event.wasClean) {
    console.error('WebSocket abnormal close:', event);
    updateStatus('disconnected', '连接异常断开');
    startAutoReconnect();
  }
};
```

### 2. 消息处理错误
```javascript
function handleMessage(data) {
  try {
    const message = JSON.parse(data);

    // 消息格式验证
    if (!message.hasOwnProperty('text') || !message.hasOwnProperty('is_final')) {
      throw new Error('Invalid message format');
    }

    processMessage(message);
  } catch (error) {
    console.error('Message processing error:', error);
    // 忽略错误消息，继续处理下一条
  }
}
```

## 用户体验设计

### 1. 视觉反馈
- **连接状态**：颜色编码的实时反馈
- **文本区分**：不同颜色和字体样式
- **操作反馈**：按钮点击效果和状态变化
- **加载动画**：连接过程中的视觉指示

### 2. 交互优化
- **自动滚动**：保持最新内容可见
- **平滑动画**：所有状态变化使用过渡效果
- **快捷键支持**：Ctrl+C复制，Ctrl+L清空
- **响应式设计**：适配不同屏幕尺寸

### 3. 可访问性
- **键盘导航**：Tab键可访问所有控件
- **屏幕阅读器**：语义化HTML和ARIA标签
- **高对比度**：确保颜色对比度符合标准
- **字体缩放**：支持浏览器字体缩放

## 测试策略设计

### 1. 功能测试场景
- 连接成功/失败/重连
- 中间稿和最终稿显示
- 复制和清空功能
- 长时间运行稳定性

### 2. 性能测试
- 大文本量滚动性能
- 频繁消息更新响应
- 内存使用情况监控
- 页面加载速度测试

### 3. 兼容性测试
- 主流浏览器兼容性
- WebSocket API支持
- ES6+语法兼容性
- 移动端适配测试