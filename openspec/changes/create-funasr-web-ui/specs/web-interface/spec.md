# FunASR Web界面规格文档

## ADDED Requirements

### Requirement: WebSocket连接管理
The system SHALL automatically connect to the local FunASR WebSocket service and display real-time connection status.

#### Scenario: Page load auto-connect
- **WHEN** user opens index.html page
- **THEN** system SHALL automatically attempt connection to ws://127.0.0.1:10095
- **AND** SHALL display "正在连接..." status with yellow indicator

#### Scenario: Connection success
- **WHEN** WebSocket connection is established successfully
- **THEN** status indicator SHALL turn green
- **AND** SHALL display "已连接" text
- **AND** SHALL hide reconnect button

#### Scenario: Connection failure
- **WHEN** WebSocket connection fails or times out (5 seconds)
- **THEN** status indicator SHALL turn red
- **AND** SHALL display "已断开" text
- **AND** SHALL display "重新连接" button

#### Scenario: Auto-reconnect
- **WHEN** WebSocket connection drops unexpectedly
- **THEN** system SHALL attempt reconnection every 5 seconds
- **AND** SHALL limit retry attempts to 10 times
- **AND** SHALL update status display for each attempt

### Requirement: 实时文本流式显示
The system SHALL receive and parse JSON messages from WebSocket, distinguish between interim and final results, and display them as streaming subtitles.

#### Scenario: Process final message
- **WHEN** receiving message with is_final: true
- **AND** message format is {"mode": "2pass-online", "text": "识别结果", "is_final": true, "timestamp": "..."}
- **THEN** system SHALL display final text on current line
- **AND** final text color SHALL be white (#D4D4D4)
- **AND** SHALL open new line below for next sentence

#### Scenario: Process interim message
- **WHEN** receiving message with is_final: false
- **AND** there is an active sentence line
- **THEN** system SHALL display interim text in gray (#888888) at end of current sentence
- **AND** interim text SHALL be replaceable by subsequent messages

#### Scenario: Interim to final transition
- **WHEN** displaying interim text
- **AND** receiving final result (is_final: true) for same sentence
- **THEN** final result SHALL replace entire sentence line content
- **AND** SHALL clear all interim text display
- **AND** SHALL maintain white color for final text

#### Scenario: Message format validation
- **WHEN** receiving WebSocket message
- **AND** message is not valid JSON format
- **THEN** system SHALL ignore message and log error
- **AND** SHALL continue processing next message

### Requirement: 用户界面和交互
The system SHALL provide a clear user interface including status indicator, text display area, and action buttons.

#### Scenario: Interface layout
- **WHEN** user opens page
- **THEN** page SHALL display status indicator at top
- **AND** SHALL display text content in central large area
- **AND** SHALL display action buttons in top-right corner
- **AND** all elements SHALL use dark theme color scheme

#### Scenario: Copy all functionality
- **WHEN** user clicks "复制全部" button
- **AND** there is displayed text content on screen
- **THEN** system SHALL copy all final text to clipboard
- **AND** SHALL display "已复制到剪贴板" notification
- **AND** notification SHALL disappear after 3 seconds

#### Scenario: Clear screen functionality
- **WHEN** user clicks "清空屏幕" button
- **AND** there is displayed text content on screen
- **THEN** system SHALL clear all displayed text
- **AND** SHALL reset text display state
- **AND** SHALL maintain WebSocket connection status

### Requirement: 性能和稳定性
The system SHALL maintain smooth and stable performance during long-term operation and large text volume scenarios.

#### Scenario: Large text volume scrolling
- **WHEN** displaying 10000+ lines of text on screen
- **AND** new text is continuously added
- **THEN** page scrolling SHALL maintain smooth performance (60fps)
- **AND** SHALL auto-scroll to bottom
- **AND** SHALL not show significant performance lag

#### Scenario: Long-term operation
- **WHEN** page runs continuously for more than 1 hour
- **AND** continuously receives and processes messages
- **THEN** memory usage SHALL remain stable
- **AND** SHALL have no memory leaks
- **AND** WebSocket connection SHALL remain stable

#### Scenario: Frequent message processing
- **WHEN** receiving 10+ WebSocket messages per second
- **AND** messages contain frequent text updates
- **THEN** UI response time SHALL remain within 100ms
- **AND** text updates SHALL not show delay
- **AND** user interaction SHALL remain responsive

### Requirement: 错误处理和恢复
The system SHALL gracefully handle various error conditions and provide user-friendly error feedback.

#### Scenario: WebSocket connection error
- **WHEN** FunASR service is not started
- **AND** page attempts WebSocket connection
- **THEN** system SHALL display "连接失败" status
- **AND** SHALL provide service not started notification
- **AND** SHALL display reconnect button

#### Scenario: Network interruption recovery
- **WHEN** WebSocket connection drops unexpectedly
- **AND** network recovers
- **THEN** auto-reconnect mechanism SHALL take effect
- **AND** SHALL resume normal text display
- **AND** SHALL update connection status to "已连接"

#### Scenario: Message processing exception
- **WHEN** receiving malformed message
- **AND** system attempts to parse message
- **THEN** system SHALL catch and log exception
- **AND** SHALL ignore malformed message
- **AND** SHALL continue processing subsequent messages

### Requirement: 可访问性和兼容性
The system SHALL support mainstream browsers and have basic accessibility features.

#### Scenario: Browser compatibility
- **WHEN** user accesses with mainstream browser
- **AND** page loading completes
- **THEN** system SHALL work normally on Chrome 80+
- **AND** SHALL work normally on Firefox 75+
- **AND** SHALL work normally on Safari 13+
- **AND** SHALL work normally on Edge 80+

#### Scenario: Keyboard navigation
- **WHEN** keyboard user accesses page
- **AND** using Tab key navigation
- **THEN** all interactive elements SHALL be focusable
- **AND** focus order SHALL be logical
- **AND** focus styling SHALL be clearly visible

#### Scenario: Responsive design
- **WHEN** user accesses on different device sizes
- **AND** page rendering completes
- **THEN** system SHALL display correctly on desktop browsers
- **AND** SHALL display correctly on tablet devices
- **AND** SHALL display correctly on mobile devices
- **AND** text size and layout SHALL adjust automatically

## MODIFIED Requirements

*无现有需求被修改，这是一个全新的项目。*

## REMOVED Requirements

*无现有需求被移除，这是一个全新的项目。*

## Implementation Constraints

1. **单文件交付**: 所有代码必须包含在一个index.html文件中
2. **CDN依赖**: 只能使用Tailwind CSS CDN作为外部依赖
3. **原生JavaScript**: 不能使用任何JavaScript框架或库
4. **本地服务**: 只能连接到127.0.0.1:10095的本地服务
5. **无后端**: 不能包含任何后端逻辑或服务器端代码

## Acceptance Criteria

1. **功能完整性**: 所有需求场景必须正常工作
2. **性能标准**: 满足所有性能要求
3. **用户体验**: 界面美观、交互流畅
4. **代码质量**: 代码结构清晰、注释完整
5. **兼容性**: 支持指定的浏览器版本
6. **错误处理**: 优雅处理所有错误情况

## Testing Requirements

1. **单元测试**: JavaScript模块功能测试
2. **集成测试**: WebSocket通信和UI集成测试
3. **性能测试**: 大文本量和长时间运行测试
4. **兼容性测试**: 跨浏览器测试
5. **可用性测试**: 用户操作流程测试

## Documentation Requirements

1. **用户手册**: 详细的使用说明
2. **部署指南**: 如何运行和使用的步骤
3. **故障排除**: 常见问题和解决方案
4. **API文档**: WebSocket消息格式说明