# VAD智能断句规格

## ADDED Requirements

### Requirement: VAD状态跟踪
系统 MUST 维护每个WebSocket连接的VAD状态，包括连续静音时长和总音频时长。系统 SHALL 在检测到满足条件的静音或超时时触发断句。

#### Scenario: 正常说话停顿后断句
**Given** 用户正在录音说话
**And** 连续检测到800ms的静音
**When** VAD检测到新的音频块
**Then** 系统应该触发断句并发送识别请求
**And** 重置VAD状态跟踪器

#### Scenario: 超时强制断句
**Given** 用户持续说话超过20秒
**And** 没有检测到足够的静音
**When** 累积音频时长达到最大阈值
**Then** 系统应该强制触发断句
**And** 发送识别请求处理累积的音频

#### Scenario: 短暂停顿不断句
**Given** 用户说话中有400ms的短暂停顿
**When** VAD检测到该停顿
**Then** 系统应该继续累积音频
**And** 不触发断句

### Requirement: VAD检测服务
系统 MUST 提供实时VAD检测功能，能够快速判断音频块是否包含语音。检测延迟 SHALL 小于100ms。

#### Scenario: 检测语音
**Given** 接收到包含语音的音频块
**When** 调用VAD检测服务
**Then** 返回 `has_speech: true`
**And** 检测延迟小于100ms

#### Scenario: 检测静音
**Given** 接收到只包含背景噪音的音频块
**When** 调用VAD检测服务
**Then** 返回 `has_speech: false`

#### Scenario: VAD检测失败降级
**Given** VAD检测服务抛出异常
**When** 检测失败
**Then** 系统应该回退到固定时长断句模式
**And** 记录错误日志

### Requirement: 可配置断句参数
系统 MUST 支持通过环境变量配置VAD断句参数。系统 SHALL 提供合理的默认值。

#### Scenario: 自定义静音阈值
**Given** 管理员设置 `VAD_SILENCE_THRESHOLD_MS=1200`
**When** 系统处理音频
**Then** 在1200ms静音后触发断句

#### Scenario: 禁用VAD断句
**Given** 管理员设置 `VAD_ENABLED=false`
**When** 系统处理音频
**Then** 使用固定时长断句模式
**And** 不调用VAD检测

#### Scenario: 修改最大时长
**Given** 管理员设置 `VAD_MAX_SEGMENT_DURATION_MS=30000`
**When** 用户持续说话
**Then** 在30秒后强制断句

### Requirement: 性能要求
VAD断句功能 MUST 在性能预算内运行。CPU使用率增加 MUST 不超过20%，整体识别延迟 SHALL 保持在2秒以内。

#### Scenario: CPU使用率限制
**Given** 启用VAD断句功能
**When** 系统处理音频流
**Then** CPU使用率增加不超过20%
**And** 整体CPU使用率保持在80%以下

#### Scenario: 延迟要求
**Given** 用户停止说话
**When** 检测到静音阈值
**Then** 在100ms内触发断句
**And** 整体识别延迟保持在2秒以内

### Requirement: 状态管理
系统 MUST 正确管理VAD状态的生命周期。连接建立时 SHALL 初始化跟踪器，断开时 MUST 清理资源。

#### Scenario: 连接建立时初始化
**Given** 新的WebSocket连接建立
**When** 连接被接受
**Then** 创建新的VAD状态跟踪器
**And** 初始化所有计数器为0

#### Scenario: 连接断开时清理
**Given** WebSocket连接断开
**When** 执行清理操作
**Then** 删除VAD状态跟踪器
**And** 释放相关内存

#### Scenario: 断句后重置
**Given** 触发断句并处理音频
**When** 识别完成
**Then** 重置VAD状态跟踪器
**And** 准备接收新的音频

### Requirement: 向后兼容
VAD断句功能 MUST 保持向后兼容。系统 SHALL 在VAD禁用或失败时回退到固定时长断句模式。

#### Scenario: 降级模式
**Given** VAD功能被禁用或失败
**When** 处理音频
**Then** 使用原有的固定时长断句逻辑
**And** 保持相同的API接口

#### Scenario: API兼容性
**Given** 客户端使用现有WebSocket协议
**When** 启用VAD功能
**Then** 客户端无需修改代码
**And** 消息格式保持不变
