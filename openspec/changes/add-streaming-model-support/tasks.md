# Implementation Tasks

## 1. 准备工作
- [x] 1.1 研究 FunASR 流式模型（paraformer-zh-streaming）的下载和使用方式
- [x] 1.2 确认流式模型的系统要求和内存占用
- [x] 1.3 阅读流式模型的 API 文档和使用示例
- [x] 1.4 下载流式模型到本地（models/paraformer-zh-streaming/目录，880MB）

## 2. 配置和脚本更新
- [x] 2.1 在 `app/core/config.py` 中添加模型配置项
  - [x] 2.1.1 添加 `models_config` 字典，包含各模型的路径和类型
  - [x] 2.1.2 添加 `default_model` 配置项
  - [x] 2.1.3 添加 `enable_model_switching` 配置项
  - [x] 2.1.4 添加 `streaming_model_path` 配置项
  - [x] 2.1.5 实现自动检测流式模型是否可用
- [x] 2.2 更新 `.env.example` 添加模型配置示例
- [x] 2.3 更新 `.env` 配置流式模型路径
- [ ] 2.4 修改 `scripts/download_model.py` 支持下载流式模型（可选）

## 3. FunASR Service 改造
- [x] 3.1 分析现有 `FunASRService` 的模型初始化逻辑
- [x] 3.2 设计模型管理策略（单例模式 vs 按需加载 vs 全部预加载）
- [x] 3.3 实现 `ModelManager` 类（替代 load_model）
- [x] 3.4 实现模型切换或选择逻辑
- [x] 3.5 修改 `initialize()` 方法支持指定模型
- [x] 3.6 添加模型状态查询方法（get_model_info）
- [x] 3.7 添加模型卸载和资源释放逻辑（ModelManager._unload_model）

## 4. WebSocket API 更新
- [x] 4.1 在 `app/main.py` WebSocket 端点添加 `model` 查询参数
- [x] 4.2 在 `app/core/websocket.py` 中处理模型参数
- [x] 4.3 添加模型验证逻辑（检查模型是否可用）
- [x] 4.4 添加模型切换的错误处理（4002/4003 错误码）

## 5. 前端更新
- [x] 5.1 在 `frontend/index.html` 添加模型选择下拉控件
- [x] 5.2 添加模型描述和说明文字
- [x] 5.3 实现模型参数传递到 WebSocket 连接
- [x] 5.4 添加模型切换状态提示

## 6. 测试
- [x] 6.1 编写流式模型的单元测试（test_model_manager.py，19个场景）
- [x] 6.2 编写模型切换的集成测试（包含在测试中）
- [x] 6.3 测试模型不存在的错误处理
- [x] 6.4 测试内存占用和资源释放
- [x] 6.5 进行端到端测试（离线模型和流式模型）

## 7. 文档
- [x] 7.1 更新 README.md 添加流式模型说明
- [x] 7.2 添加模型切换的配置说明
- [x] 7.3 更新 API 文档
- [x] 7.4 添加流式模型下载指南

## 8. 验证和部署
- [x] 8.1 本地测试流式模型功能
- [x] 8.2 验证模型切换正确性
- [x] 8.3 检查内存使用情况
- [x] 8.4 确认向后兼容性（默认离线模型）
