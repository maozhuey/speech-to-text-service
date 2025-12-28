import os
import logging
import time
import wave
import tempfile
import numpy as np
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
import asyncio

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import torch

logger = logging.getLogger(__name__)

# 全局线程池，用于执行阻塞的模型推理
# 限制线程数以避免资源耗尽
_model_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="funasr_model")

# 导入模型管理器
from app.services.model_manager import get_model_manager


class FunASRService:
    """
    FunASR 语音识别服务类

    支持多模型管理和动态切换：
    - offline: 离线模型（高精度，延迟5-10秒）
    - streaming: 流式模型（低延迟，延迟<300ms）
    """

    def __init__(self, model_dir: str = None, default_model: str = "offline"):
        # 获取项目根目录（语音转文本服务目录）
        current_file_path = os.path.dirname(os.path.abspath(__file__))  # backend/app/services/
        backend_path = os.path.dirname(os.path.dirname(current_file_path))  # backend/
        project_root = os.path.dirname(backend_path)  # 语音转文本服务/
        self.model_dir = model_dir or os.path.join(project_root, "models/damo")

        # 多模型支持
        self.default_model = default_model
        self.model_manager = None
        self.current_model = default_model

        # 保留向后兼容的属性
        self.asr_pipeline = None
        self.punc_pipeline = None
        self.vad_pipeline = None
        self.is_initialized = False

    async def initialize(self, model_name: Optional[str] = None):
        """
        初始化模型

        Args:
            model_name: 要加载的模型名称（offline 或 streaming），默认使用 default_model
        """
        from app.core.config import settings

        try:
            model_name = model_name or self.default_model
            self.current_model = model_name

            logger.info(f"开始初始化 FunASR 模型: {model_name}")

            # 初始化模型管理器
            if self.model_manager is None:
                self.model_manager = get_model_manager(max_cached_models=settings.max_cached_models)

            # 获取模型配置
            model_config = settings.get_model_config(model_name)
            if model_config is None:
                raise ValueError(f"模型 {model_name} 配置不存在")

            if not model_config.get("enabled", True):
                raise ValueError(f"模型 {model_name} 未启用")

            # 使用模型管理器加载模型
            model_dict = self.model_manager.get_model(model_name, model_config)

            if model_dict is None:
                raise RuntimeError(f"模型 {model_name} 加载失败")

            # 设置当前模型引用
            self.asr_pipeline = model_dict["asr_pipeline"]
            self.punc_pipeline = model_dict["punc_pipeline"]
            self.vad_pipeline = model_dict["vad_pipeline"]

            self.is_initialized = True
            logger.info(f"FunASR 服务初始化完成，当前模型: {model_name}")

        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            raise

    async def switch_model(self, model_name: str) -> bool:
        """
        切换到指定模型

        Args:
            model_name: 目标模型名称

        Returns:
            是否切换成功
        """
        try:
            logger.info(f"切换模型: {self.current_model} -> {model_name}")

            # 重新初始化为目标模型
            await self.initialize(model_name)
            return True

        except Exception as e:
            logger.error(f"切换模型失败: {e}")
            return False

    def _validate_audio(self, audio_data: bytes, sample_rate: int = 16000) -> np.ndarray:
        """验证和预处理音频数据"""
        try:
            # 假设输入是16位PCM音频数据
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

            # 归一化到[-1, 1]范围
            audio_array = audio_array / 32768.0

            # 检查音频长度是否太短
            if len(audio_array) < sample_rate * 0.1:  # 小于0.1秒
                raise ValueError("音频长度太短")

            return audio_array

        except Exception as e:
            logger.error(f"音频数据验证失败: {e}")
            raise ValueError(f"无效的音频数据: {str(e)}")

    def _save_temp_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """保存临时音频文件"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)

        try:
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(1)  # 单声道
                wf.setsampwidth(2)  # 16位
                wf.setframerate(sample_rate)

                # 转换回16位整数格式
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())

            return temp_file.name

        except Exception as e:
            temp_file.close()
            os.unlink(temp_file.name)
            logger.error(f"保存临时音频文件失败: {e}")
            raise

    async def recognize_speech(self, audio_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """识别语音并返回结果"""
        if not self.is_initialized:
            await self.initialize()

        start_time = time.time()
        temp_file = None

        try:
            # 验证和预处理音频
            audio_array = self._validate_audio(audio_data, sample_rate)

            # 保存临时音频文件
            temp_file = self._save_temp_audio(audio_array, sample_rate)

            # 使用线程池执行阻塞的模型推理，避免阻塞事件循环
            logger.info("开始语音识别...")
            loop = asyncio.get_event_loop()

            # 在线程池中执行ASR识别
            asr_result = await loop.run_in_executor(
                _model_executor,
                self.asr_pipeline,
                temp_file
            )

            # 提取识别文本
            if isinstance(asr_result, dict) and 'text' in asr_result:
                text = asr_result['text']
            elif isinstance(asr_result, list) and len(asr_result) > 0:
                text = asr_result[0].get('text', '')
            else:
                text = str(asr_result)

            # 清理文本（移除可能的空白字符）
            text = text.strip()

            # 如果有识别结果，添加标点符号
            if text:
                try:
                    logger.info(f"识别文本（加标点前）: {text}")
                    # 在线程池中执行标点符号恢复
                    punc_result = await loop.run_in_executor(
                        _model_executor,
                        self.punc_pipeline,
                        text
                    )
                    logger.info(f"标点结果: {punc_result}")
                    if isinstance(punc_result, dict) and 'text' in punc_result:
                        text = punc_result['text']
                        logger.info(f"识别文本（加标点后）: {text}")
                except Exception as e:
                    logger.error(f"标点符号添加失败: {e}", exc_info=True)
            else:
                logger.warning("语音识别未返回文本结果")

            processing_time = time.time() - start_time

            # 返回识别结果
            result = {
                "success": True,
                "text": text,
                "speaker": "speaker_1",
                "is_final": True,
                "confidence": 0.95,  # FunASR通常不直接提供置信度，使用默认值
                "processing_time": processing_time,
                "timestamp": {
                    "start": start_time,
                    "end": time.time()
                }
            }

            logger.info(f"语音识别完成，耗时: {processing_time:.2f}秒，结果: {text[:50]}...")
            return result

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "speaker": "speaker_1",
                "is_final": True,
                "confidence": 0.0
            }

        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"已清理临时文件: {temp_file}")
                except OSError as e:
                    logger.error(f"清理临时文件失败 {temp_file}: {e}")
                    # 可以考虑添加到清理队列，定期重试
                except Exception as e:
                    logger.error(f"清理临时文件时发生意外错误 {temp_file}: {e}")

    async def batch_recognize(self, audio_chunks: List[bytes], sample_rate: int = 16000) -> List[Dict[str, Any]]:
        """批量识别多个音频片段"""
        results = []

        for i, chunk in enumerate(audio_chunks):
            try:
                result = await self.recognize_speech(chunk, sample_rate)
                result["chunk_index"] = i
                results.append(result)
            except Exception as e:
                logger.error(f"第{i}个音频片段识别失败: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "text": "",
                    "chunk_index": i,
                    "is_final": True
                })

        return results

    async def detect_voice_activity(self, audio_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """检测语音活动（VAD）"""
        if not self.is_initialized:
            await self.initialize()

        try:
            # 验证音频数据
            audio_array = self._validate_audio(audio_data, sample_rate)

            # 暂时保存临时文件（用于日志）
            temp_file = self._save_temp_audio(audio_array, sample_rate)

            # 执行真实的VAD检测
            logger.info("开始VAD检测...")
            vad_result = self.vad_pipeline(temp_file)

            # 清理临时文件
            os.unlink(temp_file)

            return {
                "success": True,
                "has_speech": bool(vad_result.get('speech', [])),
                "speech_segments": vad_result.get('speech', [])
            }

        except Exception as e:
            logger.error(f"VAD检测失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "has_speech": False
            }

    async def detect_voice_activity_realtime(self, audio_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        实时VAD检测（优化版，用于音频流处理）

        与detect_voice_activity的区别：
        - 不创建临时文件，直接处理音频数据
        - 返回更简洁的结果
        - 适合高频调用场景

        Args:
            audio_data: 音频数据（PCM格式）
            sample_rate: 采样率

        Returns:
            dict: {"has_speech": bool, "success": bool}
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            # 快速验证：检查音频数据长度是否太短
            if len(audio_data) < sample_rate * 0.1:  # 小于0.1秒
                return {"success": True, "has_speech": False}

            # 验证音频数据
            audio_array = self._validate_audio(audio_data, sample_rate)

            # 简化的VAD检测：基于能量阈值快速判断
            # 计算音频能量
            energy = float(np.mean(audio_array ** 2))

            # 动态阈值（基于典型语音能量）
            energy_threshold = 0.001  # 可根据实际环境调整

            has_speech = energy > energy_threshold

            # 对于边界情况，使用完整的VAD检测
            if 0.0005 < energy < 0.002:  # 边界区域
                temp_file = None
                try:
                    temp_file = self._save_temp_audio(audio_array, sample_rate)
                    vad_result = self.vad_pipeline(temp_file)
                    has_speech = bool(vad_result.get('speech', []))
                except (OSError, IOError) as file_err:
                    logger.warning(f"VAD文件操作失败: {file_err}，使用能量阈值结果")
                except Exception as vad_err:
                    logger.warning(f"VAD检测失败: {vad_err}，使用能量阈值结果")
                finally:
                    # 确保临时文件被清理
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.unlink(temp_file)
                            logger.debug(f"已清理VAD临时文件: {temp_file}")
                        except OSError as e:
                            logger.error(f"清理VAD临时文件失败 {temp_file}: {e}")

            return {"success": True, "has_speech": has_speech}

        except Exception as e:
            logger.warning(f"实时VAD检测失败，使用默认值: {e}")
            # 检测失败时默认返回True（保守策略，避免丢失语音）
            return {"success": False, "has_speech": True}

    def cleanup(self):
        """清理资源"""
        # 清理模型资源
        self.asr_pipeline = None
        self.punc_pipeline = None
        self.vad_pipeline = None
        self.is_initialized = False

        # 清理模型管理器
        if self.model_manager is not None:
            self.model_manager.cleanup()
            self.model_manager = None

        logger.info("FunASR 服务资源已清理")

        # 清理线程池（释放资源）
        global _model_executor
        if _model_executor is not None:
            try:
                _model_executor.shutdown(wait=False)
                logger.info("模型线程池已关闭")
            except Exception as e:
                logger.warning(f"关闭线程池时出错: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息

        Returns:
            包含当前模型名称、类型和状态的字典
        """
        return {
            "current_model": self.current_model,
            "is_initialized": self.is_initialized,
            "loaded_models": self.model_manager.get_loaded_models() if self.model_manager else []
        }


# 创建全局服务实例（使用配置中的默认模型）
from app.core.config import settings
funasr_service = FunASRService(default_model=settings.default_model)