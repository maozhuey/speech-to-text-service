# 实时标点显示规格

## ADDED Requirements

### Requirement: 中间结果显示
系统 MUST 在识别过程中实时显示中间识别结果。中间结果 SHOULD 使用灰色或斜体样式，与最终结果区分。

#### Scenario: 显示中间结果
**Given** 用户正在说话
**And** 后端返回中间识别结果（`is_final: false`）
**When** 前端接收到中间结果
**Then** 系统应该显示灰色斜体的中间文本
**And** 中间文本位于文本显示区域底部
**And** 自动滚动到最新内容

#### Scenario: 中间结果更新
**Given** 显示了中间结果"今天天气"
**And** 用户继续说话
**And** 后端返回新的中间结果"今天天气怎么样"
**When** 前端接收到新结果
**Then** 系统应该更新中间文本为"今天天气怎么样"
**And** 保持灰色斜体样式

#### Scenario: 中间结果被最终结果替换
**Given** 显示了中间结果"今天天气怎么样"
**And** 后端返回最终结果（`is_final: true`）
**When** 前端接收到最终结果
**Then** 系统应该移除中间结果显示
**And** 显示带有标点的最终结果"今天天气怎么样？"
**And** 最终结果使用白色正常样式

### Requirement: 流式识别支持
后端系统 SHOULD 支持流式识别，在识别过程中返回中间结果。如果FunASR不支持流式API，系统 MUST 提供降级方案。

#### Scenario: 流式识别返回中间结果
**Given** FunASR支持流式识别
**When** 开始识别音频
**Then** 系统应该返回多个中间结果
**And** 每个中间结果包含 `is_final: false`
**And** 最后返回最终结果 `is_final: true`

#### Scenario: 流式识别不支持时降级
**Given** FunASR不支持流式识别
**When** 开始识别音频
**Then** 系统应该使用现有的整句识别
**And** 前端显示"识别中..."提示
**And** 识别完成后显示最终结果

#### Scenario: 中间结果包含临时标点
**Given** 返回中间结果
**When** 中间结果包含可能的标点位置
**Then** 系统应该显示临时标点符号
**And** 临时标点可能不准确（以最终结果为准）

### Requirement: 实时性能
中间结果显示 MUST 满足实时性能要求。

#### Scenario: 实时延迟要求
**Given** 用户说话
**When** 产生中间识别结果
**Then** 中间结果延迟 MUST 小于500ms
**And** 更新频率 SHOULD 为每200-300ms

#### Scenario: DOM更新性能
**Given** 每秒更新3-5次中间结果
**When** 更新DOM元素
**Then** 页面 MUST 保持流畅（60fps）
**And** 不阻塞用户操作

### Requirement: 样式区分
中间结果和最终结果 MUST 有明显的视觉区分。

#### Scenario: 中间结果样式
**Given** 显示中间结果
**When** 渲染中间结果文本
**Then** 文本颜色应该是灰色（#9CA3AF）
**And** 字体样式应该是斜体
**And** 透明度应该是80%

#### Scenario: 最终结果样式
**Given** 显示最终结果
**When** 渲染最终结果文本
**Then** 文本颜色应该是白色（#FFFFFF）
**And** 字体样式应该是正常
**And** 透明度应该是100%

#### Scenario: 过渡动画
**Given** 中间结果被最终结果替换
**When** 执行替换
**Then** 应该有平滑的淡入淡出动画
**And** 动画时长应该是300ms

### Requirement: 错误处理
系统 MUST 优雅处理中间结果显示过程中的错误。

#### Scenario: 中间结果解析失败
**Given** 后端返回格式错误的中间结果
**When** 前端尝试解析
**Then** 系统应该忽略该结果
**And** 记录错误日志
**And** 不影响后续识别

#### Scenario: 中间结果丢失
**Given** 发送了中间结果
**When** 网络中断导致结果丢失
**Then** 系统应该等待下一个结果
**And** 不显示错误提示

#### Scenario: 识别失败处理
**Given** 识别过程中发生错误
**When** 后端返回错误消息
**Then** 系统应该清除中间结果
**And** 显示错误提示
**And** 保持识别状态（用户可继续说话）

### Requirement: 向后兼容
系统 MUST 保持向后兼容性。

#### Scenario: 旧版本客户端
**Given** 旧版本客户端（不支持中间结果）
**When** 连接到新服务器
**Then** 客户端应该忽略 `is_final: false` 消息
**And** 正常显示最终结果

#### Scenario: 新版本客户端连接旧服务器
**Given** 新版本客户端
**When** 连接到旧服务器（无中间结果）
**Then** 客户端应该正常工作
**And** 不显示中间结果
**And** 等待最终结果
