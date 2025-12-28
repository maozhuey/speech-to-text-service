# 实施任务清单

## 阶段1：VAD状态跟踪器实现
- [ ] 创建 `VADStateTracker` 类
  - [ ] 实现 `__init__` 初始化方法
  - [ ] 实现 `process_audio_chunk` 核心逻辑
  - [ ] 实现 `reset` 重置方法
  - [ ] 添加单元测试

## 阶段2：配置管理
- [ ] 在 `config.py` 中添加VAD配置项
  - [ ] `VAD_SILENCE_THRESHOLD_MS` (默认800ms)
  - [ ] `VAD_MAX_SEGMENT_DURATION_MS` (默认20000ms)
  - [ ] `VAD_ENABLED` (默认true)
- [ ] 更新 `.env.example` 文件
- [ ] 验证配置加载正确

## 阶段3：WebSocket集成
- [ ] 在 `ConnectionManager` 中添加VAD状态跟踪
  - [ ] 创建 `vad_trackers` 字典
  - [ ] 在 `connect()` 时初始化tracker
  - [ ] 在 `disconnect()` 时清理tracker
- [ ] 修改 `process_audio()` 方法
  - [ ] 调用VAD检测
  - [ ] 更新VAD状态
  - [ ] 判断是否触发断句
- [ ] 实现降级策略
  - [ ] VAD失败时回退到固定时长
  - [ ] 添加日志记录

## 阶段4：VAD检测服务
- [ ] 在 `funasr_service.py` 中实现实时VAD
  - [ ] 创建 `detect_voice_activity_realtime()` 方法
  - [ ] 处理小块音频数据（4096采样）
  - [ ] 返回简洁的结果格式
- [ ] 性能优化
  - [ ] 确保VAD调用不阻塞主流程
  - [ ] 添加性能监控日志

## 阶段5：前端优化（可选）
- [ ] 显示断句状态
  - [ ] 添加"检测中"提示
  - [ ] 显示"正在识别..."状态
- [ ] 优化用户体验
  - [ ] 添加视觉反馈

## 阶段6：测试
- [ ] 单元测试
  - [ ] `VADStateTracker` 测试
  - [ ] VAD检测服务测试
  - [ ] 达到80%覆盖率
- [ ] 集成测试
  - [ ] 端到端断句测试
  - [ ] 验收场景测试
- [ ] 性能测试
  - [ ] CPU使用率测试
  - [ ] 延迟测试
  - [ ] 并发测试

## 阶段7：文档和发布
- [ ] 更新API文档
- [ ] 添加配置说明
- [ ] 编写用户指南
- [ ] 提交代码审查
- [ ] 合并到主分支
