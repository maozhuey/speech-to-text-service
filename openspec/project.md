# Project Context

## Purpose
开发一个语音转文本基础服务，以方便其他应用在需要语音转文本服务时调用该基础服务。该服务主要用于中文场景的短文本语音输入以及长时间的会议实时记录。

## Tech Stack
- **前端**: HTML + Tailwind CSS + Vanilla JavaScript
- **后端**: Python + FastAPI
- **语音识别**: FunASR (阿里巴巴达摩院)
- **实时通信**: WebSocket
- **音频处理**: WebRTC/Stream
- **部署**: Docker (可选)

## Project Conventions

### Code Style
- Python: 遵循PEP 8规范
- JavaScript: 使用ES6+语法，ESLint配置
- 命名: 使用有意义的英文变量名，注释使用中文
- 文件结构: 模块化设计，单一职责原则

### Architecture Patterns
- 前后端分离架构
- RESTful API设计
- WebSocket实时通信
- 微服务思想（未来扩展）

### Testing Strategy
- 单元测试覆盖率 > 80%
- 集成测试覆盖核心功能
- 性能测试验证并发能力
- 用户体验测试

### Git Workflow
- 主分支: main
- 功能分支: feature/功能名
- 修复分支: fix/问题描述
- 提交信息: 使用约定式提交格式

## Domain Context
- **主要应用场景**: 中文语音转文本
- **短文本输入**: 语音输入法、语音搜索等
- **长时间记录**: 会议记录、访谈记录、讲座转写
- **说话人分离**: 多人对话场景下的说话人识别
- **标点符号**: 自动添加中文标点符号
- **时间戳**: 记录每句话的时间信息

## Important Constraints
- **硬件要求**: M2 Pro (16GB RAM) MacBook Pro完美支持
- **并发连接**: 最大支持2个并发连接
- **实时性**: 语音转文本延迟 < 2秒
- **准确性**: 中文识别准确率 > 95%
- **响应时间**: API响应时间 < 500ms

## External Dependencies
- **FunASR**: 阿里巴巴达摩院语音识别框架
- **浏览器**: 支持现代浏览器（Chrome 80+, Firefox 75+, Safari 13+）
- **音频设备**: 需要麦克风权限
- **网络**: WebSocket连接要求稳定网络环境
