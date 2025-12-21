#!/usr/bin/env python3
"""
启动语音转文本服务的脚本
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 9):
        print("错误: 需要Python 3.9或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    return True

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import funasr
        import modelscope
        print("所有依赖已安装!")
        return True
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_models():
    """检查模型是否下载"""
    models_dir = project_root / "models"
    required_models = [
        "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
    ]

    missing_models = []
    for model in required_models:
        model_path = models_dir / model
        if not model_path.exists():
            missing_models.append(model)

    if missing_models:
        print("缺少以下模型:")
        for model in missing_models:
            print(f"  - {model}")
        print("请运行: python scripts/download_models.py")
        return False
    else:
        print("所有模型已下载!")
        return True

def create_directories():
    """创建必要的目录"""
    directories = [
        "logs",
        "temp"
    ]

    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)

def start_backend():
    """启动后端服务"""
    backend_dir = project_root / "backend"
    os.chdir(backend_dir)

    print("启动后端服务...")
    print("服务地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws")
    print("按 Ctrl+C 停止服务")

    try:
        # 启动uvicorn服务器
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")

def main():
    """主函数"""
    print("语音转文本服务启动工具")
    print("=" * 40)

    # 检查环境
    if not check_python_version():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    if not check_models():
        print("模型检查失败，但可以继续启动服务（部分功能可能不可用）")

    # 创建目录
    create_directories()

    # 启动服务
    start_backend()

if __name__ == "__main__":
    main()