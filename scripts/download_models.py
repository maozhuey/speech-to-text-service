#!/usr/bin/env python3
"""
下载FunASR模型的脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def download_models():
    """下载必要的FunASR模型"""
    try:
        from modelscope import snapshot_download

        # 创建模型目录
        models_dir = project_root / "models"
        models_dir.mkdir(exist_ok=True)

        print("开始下载FunASR模型...")

        # 1. 下载语音识别模型
        print("正在下载语音识别模型...")
        speech_model = snapshot_download(
            'damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
            cache_dir=str(models_dir)
        )
        print(f"语音识别模型下载完成: {speech_model}")

        # 2. 下载VAD模型
        print("正在下载VAD模型...")
        vad_model = snapshot_download(
            'damo/speech_fsmn_vad_zh-cn-16k-common-pytorch',
            cache_dir=str(models_dir)
        )
        print(f"VAD模型下载完成: {vad_model}")

        # 3. 下载标点符号模型
        print("正在下载标点符号模型...")
        punc_model = snapshot_download(
            'damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',
            cache_dir=str(models_dir)
        )
        print(f"标点符号模型下载完成: {punc_model}")

        print("所有模型下载完成！")
        return True

    except ImportError:
        print("错误: 请先安装modelscope包")
        print("运行: pip install modelscope")
        return False
    except Exception as e:
        print(f"模型下载失败: {e}")
        return False

def check_models():
    """检查模型是否存在"""
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
        return False
    else:
        print("所有模型都已下载!")
        return True

def main():
    """主函数"""
    print("FunASR模型下载工具")
    print("=" * 40)

    # 检查模型是否存在
    if check_models():
        print("模型已存在，无需下载")
        return

    # 下载模型
    if download_models():
        print("模型下载成功!")
    else:
        print("模型下载失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()