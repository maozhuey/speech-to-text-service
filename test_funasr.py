#!/usr/bin/env python3
"""测试FunASR模型是否正常工作"""
import os
import sys
import asyncio
import logging

# 添加backend目录到Python路径
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_funasr_service():
    """测试FunASR服务"""
    try:
        from app.services.funasr_service import funasr_service

        print("开始测试FunASR服务...")

        # 先检查路径
        # file在 /Users/hanchanglin/AI编程代码库/apps/语音转文本服务/test_funasr.py
        # 所以项目根目录就是当前文件的目录
        project_root = os.path.dirname(os.path.abspath(__file__))
        print(f"项目根目录: {project_root}")

        model_dir = os.path.join(project_root, "models/damo")
        print(f"模型目录: {model_dir}")

        models_to_check = [
            "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
            "speech_fsmn_vad_zh-cn-16k-common-pytorch"
        ]

        for model in models_to_check:
            path = os.path.join(model_dir, model)
            exists = os.path.exists(path)
            print(f'{model}: {"存在" if exists else "不存在"} ({path})')

        # 初始化服务
        print("正在初始化FunASR模型...")

        # 手动设置模型路径
        funasr_service.model_dir = model_dir
        print(f"FunASR服务模型目录设置为: {funasr_service.model_dir}")

        await funasr_service.initialize()

        print("✅ FunASR服务初始化成功！")
        print(f"ASR Pipeline: {type(funasr_service.asr_pipeline)}")
        print(f"Punctuation Pipeline: {type(funasr_service.punc_pipeline)}")
        print(f"VAD Pipeline: {type(funasr_service.vad_pipeline)}")

        return True

    except Exception as e:
        print(f"❌ FunASR服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_funasr_service())
    if success:
        print("\n🎉 FunASR模型测试成功！所有模型都已正确加载！")
        sys.exit(0)
    else:
        print("\n💥 FunASR模型测试失败！")
        sys.exit(1)