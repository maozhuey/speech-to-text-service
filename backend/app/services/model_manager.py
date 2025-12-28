"""
模型管理器

管理多个 FunASR 模型的加载、卸载和缓存。
使用 LRU (Least Recently Used) 缓存策略，避免内存溢出。
"""

import os
import logging
import threading
from typing import Optional, Dict, Any
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import torch

logger = logging.getLogger(__name__)


class ModelManager:
    """
    模型管理器

    负责管理多个 FunASR 模型的生命周期，包括：
    - 按需加载模型
    - LRU 缓存管理（最多缓存 max_cached_models 个模型）
    - 线程安全的模型访问
    - 资源清理
    """

    def __init__(self, max_cached_models: int = 2):
        """
        初始化模型管理器

        Args:
            max_cached_models: 最大缓存的模型数量
        """
        self.max_cached_models = max_cached_models
        self.loaded_models: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="model_loader")

        logger.info(f"ModelManager 初始化完成，最大缓存模型数: {max_cached_models}")

    def get_model(self, model_name: str, model_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        获取模型，按需加载

        如果模型已加载，更新 LRU 顺序并返回；
        如果模型未加载，加载它并管理缓存。

        Args:
            model_name: 模型名称（如 "offline", "streaming"）
            model_config: 模型配置字典，包含 path, type 等信息

        Returns:
            模型字典，包含 asr_pipeline, punc_pipeline, vad_pipeline，失败返回 None
        """
        with self._lock:
            # 检查模型是否已加载
            if model_name in self.loaded_models:
                # 更新 LRU 顺序（移动到末尾）
                self.loaded_models.move_to_end(model_name)
                logger.debug(f"模型 {model_name} 已在缓存中")
                return self.loaded_models[model_name]

            # 检查模型配置是否有效
            if not model_config.get("enabled", True):
                logger.warning(f"模型 {model_name} 未启用")
                return None

            model_path = model_config.get("path")
            if not model_path:
                logger.error(f"模型 {model_name} 配置中缺少 path")
                return None

            # 检查模型文件是否存在
            if not os.path.exists(model_path):
                logger.error(f"模型路径不存在: {model_path}")
                return None

            # 加载新模型
            logger.info(f"开始加载模型 {model_name} ({model_config.get('display_name', model_name)})...")
            model_dict = self._load_model(model_name, model_path, model_config)

            if model_dict is None:
                logger.error(f"模型 {model_name} 加载失败")
                return None

            # 检查缓存限制，如果超出则卸载最久未使用的模型
            if len(self.loaded_models) >= self.max_cached_models:
                oldest_model_name = next(iter(self.loaded_models))
                logger.info(f"缓存已满，卸载最久未使用的模型: {oldest_model_name}")
                self._unload_model(oldest_model_name)

            # 缓存新加载的模型
            self.loaded_models[model_name] = model_dict
            logger.info(f"模型 {model_name} 加载完成并已缓存")

            return model_dict

    def _load_model(self, model_name: str, model_path: str, model_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        加载单个模型

        Args:
            model_name: 模型名称
            model_path: 模型路径
            model_config: 模型配置

        Returns:
            模型字典，包含 asr_pipeline, punc_pipeline, vad_pipeline
        """
        try:
            # 初始化语音识别模型
            asr_pipeline = pipeline(
                task=Tasks.auto_speech_recognition,
                model=model_path
            )
            logger.info(f"  - ASR 模型加载完成")

            # 标点符号模型使用共享的（不按模型类型区分）
            # 从配置中获取标点模型路径，或使用默认路径
            from app.core.config import settings
            punc_model_path = model_config.get("punc_model_path", settings.punc_model_path)
            vad_model_path = model_config.get("vad_model_path", settings.vad_model_path)

            # 初始化标点符号恢复模型
            punc_pipeline = pipeline(
                task=Tasks.punctuation,
                model=punc_model_path
            )
            logger.info(f"  - 标点符号模型加载完成")

            # 初始化 VAD 模型
            vad_pipeline = pipeline(
                task=Tasks.voice_activity_detection,
                model=vad_model_path
            )
            logger.info(f"  - VAD 模型加载完成")

            return {
                "asr_pipeline": asr_pipeline,
                "punc_pipeline": punc_pipeline,
                "vad_pipeline": vad_pipeline,
                "model_name": model_name,
                "model_type": model_config.get("type", "offline")
            }

        except Exception as e:
            logger.error(f"加载模型 {model_name} 时发生错误: {e}", exc_info=True)
            return None

    def _unload_model(self, model_name: str) -> bool:
        """
        卸载模型并释放资源

        Args:
            model_name: 要卸载的模型名称

        Returns:
            是否成功卸载
        """
        if model_name not in self.loaded_models:
            logger.warning(f"模型 {model_name} 未加载，无需卸载")
            return False

        try:
            model_dict = self.loaded_models.pop(model_name)

            # 清理模型引用
            model_dict["asr_pipeline"] = None
            model_dict["punc_pipeline"] = None
            model_dict["vad_pipeline"] = None

            # 触发垃圾回收
            import gc
            gc.collect()

            # 如果有 CUDA，清理 GPU 缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info(f"模型 {model_name} 已卸载，资源已释放")
            return True

        except Exception as e:
            logger.error(f"卸载模型 {model_name} 时发生错误: {e}")
            return False

    def is_model_loaded(self, model_name: str) -> bool:
        """检查模型是否已加载"""
        with self._lock:
            return model_name in self.loaded_models

    def get_loaded_models(self) -> list[str]:
        """获取已加载的模型列表"""
        with self._lock:
            return list(self.loaded_models.keys())

    def cleanup(self):
        """清理所有加载的模型"""
        with self._lock:
            model_names = list(self.loaded_models.keys())
            for model_name in model_names:
                self._unload_model(model_name)

            # 关闭线程池
            self._executor.shutdown(wait=False)
            logger.info("ModelManager 资源已全部清理")


# 创建全局模型管理器实例
_model_manager: Optional[ModelManager] = None
_manager_lock = threading.Lock()


def get_model_manager(max_cached_models: int = 2) -> ModelManager:
    """
    获取全局模型管理器实例（单例模式）

    Args:
        max_cached_models: 最大缓存的模型数量

    Returns:
        ModelManager 实例
    """
    global _model_manager
    if _model_manager is None:
        with _manager_lock:
            if _model_manager is None:
                _model_manager = ModelManager(max_cached_models=max_cached_models)
    return _model_manager
