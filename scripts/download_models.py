#!/usr/bin/env python3
"""
下载FunASR模型的脚本

支持下载的模型：
- offline: 离线模型（高精度，延迟5-10秒）
- streaming: 流式模型（低延迟，延迟<800ms）
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 模型配置
MODEL_CONFIGS: Dict[str, Dict[str, str]] = {
    "offline": {
        "name": "离线模型（高精度）",
        "asr_model": "damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "vad_model": "damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "punc_model": "damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "description": "适合会议记录、文档转录，延迟5-10秒",
        "estimated_size": "2-3GB"
    },
    "streaming": {
        "name": "流式模型（低延迟）",
        "asr_model": "damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "vad_model": "damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "punc_model": "damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        "description": "适合语音输入、实时字幕，延迟<800ms",
        "estimated_size": "2-3GB",
        "note": "流式模型需要额外配置，请参考 README.md"
    }
}


class DownloadError(Exception):
    """下载错误基类"""
    pass


class ValidationError(DownloadError):
    """验证错误"""
    pass


def check_disk_space(required_space_gb: float = 10) -> bool:
    """检查磁盘空间是否充足

    Args:
        required_space_gb: 需要的磁盘空间（GB）

    Returns:
        磁盘空间是否充足
    """
    try:
        stat = shutil.disk_usage(str(project_root))
        free_space_gb = stat.free / (1024 ** 3)

        if free_space_gb < required_space_gb:
            logger.error(
                f"磁盘空间不足：需要 {required_space_gb}GB，"
                f"可用 {free_space_gb:.2f}GB"
            )
            return False

        logger.info(f"磁盘空间检查通过：可用 {free_space_gb:.2f}GB")
        return True
    except Exception as e:
        logger.error(f"检查磁盘空间失败: {e}")
        return False


def validate_model_type(model_type: Optional[str]) -> str:
    """验证模型类型

    Args:
        model_type: 模型类型

    Returns:
        验证后的模型类型

    Raises:
        ValidationError: 模型类型无效
    """
    if model_type is None:
        raise ValidationError("模型类型不能为 None")

    if not isinstance(model_type, str):
        raise ValidationError(
            f"模型类型必须是字符串，收到: {type(model_type).__name__}"
        )

    model_type = model_type.strip().lower()
    if model_type not in MODEL_CONFIGS:
        raise ValidationError(
            f"不支持的模型类型: '{model_type}'。"
            f"支持的类型: {', '.join(MODEL_CONFIGS.keys())}"
        )

    return model_type


def download_model(model_name: str, cache_dir: Path) -> str:
    """下载单个模型

    Args:
        model_name: 模型名称
        cache_dir: 缓存目录

    Returns:
        模型路径

    Raises:
        DownloadError: 下载失败
    """
    try:
        from modelscope import snapshot_download

        logger.info(f"正在下载 {model_name}...")
        model_path = snapshot_download(
            model_name,
            cache_dir=str(cache_dir)
        )
        logger.info(f"  下载完成: {model_path}")
        return model_path

    except ImportError as e:
        raise DownloadError("缺少 modelscope 包，请运行: pip install modelscope")
    except Exception as e:
        raise DownloadError(f"下载 {model_name} 失败: {e}")


def download_models(model_type: str = "offline", force: bool = False) -> bool:
    """下载指定的FunASR模型

    Args:
        model_type: 模型类型，"offline" 或 "streaming"
        force: 是否强制重新下载

    Returns:
        是否下载成功
    """
    # 验证输入
    try:
        model_type = validate_model_type(model_type)
    except ValidationError as e:
        logger.error(str(e))
        return False

    config = MODEL_CONFIGS[model_type]

    # 检查流式模型配置提示
    if model_type == "streaming" and "note" in config:
        logger.warning(f"提示: {config['note']}")

    # 检查磁盘空间
    if not check_disk_space():
        return False

    # 创建模型目录
    models_dir = project_root / "models"
    models_dir.mkdir(exist_ok=True)

    # 检查模型是否已存在
    if not force and check_models(model_type, verify_content=False):
        logger.info(f"{config['name']} 已存在，使用 --force 选项强制重新下载")
        return True

    try:
        logger.info(f"开始下载 {config['name']}...")
        logger.info(f"说明: {config['description']}")
        logger.info(f"预估大小: {config['estimated_size']}")
        logger.info("-" * 50)

        # 下载三个子模型
        models = {
            "语音识别": config['asr_model'],
            "VAD": config['vad_model'],
            "标点符号": config['punc_model']
        }

        for model_desc, model_name in models.items():
            logger.info(f"正在下载{model_desc}模型...")
            download_model(model_name, models_dir)

        logger.info("-" * 50)
        logger.info(f"✓ {config['name']} 下载完成！")
        return True

    except DownloadError as e:
        logger.error(str(e))
        return False
    except Exception as e:
        logger.error(f"未知错误: {e}", exc_info=True)
        return False


def check_models(model_type: Optional[str] = None, verify_content: bool = False) -> bool:
    """检查模型是否存在

    Args:
        model_type: 要检查的模型类型，None 表示检查所有模型
        verify_content: 是否验证模型内容完整性

    Returns:
        所有模型是否都存在
    """
    models_dir = project_root / "models"

    if not models_dir.exists():
        logger.warning(f"模型目录不存在: {models_dir}")
        return False

    # 确定要检查的模型
    if model_type:
        try:
            model_type = validate_model_type(model_type)
            configs_to_check = {model_type: MODEL_CONFIGS[model_type]}
        except ValidationError:
            return False
    else:
        configs_to_check = MODEL_CONFIGS

    all_exist = True
    for model_type_key, config in configs_to_check.items():
        logger.info(f"检查 {config['name']}:")

        # 提取模型名称
        def extract_model_name(model_path: str) -> str:
            """从模型路径中提取模型名称"""
            parts = model_path.split('/')
            return parts[-1]

        required_models = [
            extract_model_name(config['asr_model']),
            extract_model_name(config['vad_model']),
            extract_model_name(config['punc_model'])
        ]

        missing_models = []
        for model in required_models:
            model_path = models_dir / model

            if not model_path.exists():
                missing_models.append(model)
            elif verify_content:
                # 验证关键文件
                key_files = ['config.yaml']
                if not all((model_path / f).exists() for f in key_files):
                    missing_models.append(f"{model} (不完整)")

        if missing_models:
            logger.warning(f"  [缺失] 以下模型未下载:")
            for model in missing_models:
                logger.warning(f"    - {model}")
            all_exist = False
        else:
            logger.info(f"  [完成] 所有模型都已下载")

    return all_exist


def list_models() -> None:
    """列出所有可用的模型类型"""
    logger.info("可用的模型类型:")
    logger.info("-" * 50)
    for model_type, config in MODEL_CONFIGS.items():
        logger.info(f"\n[{model_type}] {config['name']}")
        logger.info(f"  说明: {config['description']}")
        logger.info(f"  大小: {config['estimated_size']}")
        if "note" in config:
            logger.info(f"  注意: {config['note']}")
    logger.info("-" * 50)


def main() -> int:
    """主函数

    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="FunASR模型下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python download_models.py                  # 下载离线模型（默认）
  python download_models.py -t streaming      # 查看流式模型配置
  python download_models.py --check           # 检查模型是否存在
  python download_models.py --list            # 列出所有可用模型
  python download_models.py --force           # 强制重新下载
        """
    )

    parser.add_argument(
        "-t", "--type",
        choices=["offline", "streaming"],
        default="offline",
        help="模型类型 (默认: offline)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查模型是否存在"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的模型类型"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新下载，即使模型已存在"
    )

    args = parser.parse_args()

    logger.info("FunASR模型下载工具")
    logger.info("=" * 50)

    if args.list:
        list_models()
        return 0

    # 互斥选项检查
    if args.check and args.force:
        parser.error("--check 和 --force 不能同时使用")

    if args.check:
        if check_models(args.type):
            logger.info("\n✓ 模型检查通过")
            return 0
        else:
            logger.error("\n✗ 模型检查失败，请运行下载命令")
            return 1

    # 下载模型
    config = MODEL_CONFIGS[args.type]
    logger.info(f"准备下载: {config['name']}\n")

    if download_models(args.type, args.force):
        logger.info("\n模型下载成功!")
        logger.info(f"可以使用以下命令启动服务:")
        logger.info(f"  python scripts/start_service.py --model {args.type}")
        return 0
    else:
        logger.error("\n模型下载失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
