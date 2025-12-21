#!/usr/bin/env python3
"""启动后端服务脚本"""
import os
import sys

# 添加backend目录到Python路径
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 切换到backend目录
os.chdir(backend_path)

# 导入配置
if __name__ == "__main__":
    from app.core.config import settings

    print(f"启动后端服务...")
    print(f"项目根目录: {project_root}")
    print(f"Backend目录: {backend_path}")
    print(f"模型目录: {os.path.join(project_root, 'models/damo')}")
    print(f"服务将在 http://{settings.host}:{settings.port} 启动")

    # 使用子进程启动uvicorn
    import subprocess
    import os

    env = os.environ.copy()
    env['PYTHONPATH'] = backend_path + ':' + project_root

    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", settings.host,
        "--port", str(settings.port),
        "--reload",
        "--log-level", settings.log_level.lower()
    ], env=env)