import os
import logging
import time
import wave
import tempfile
import numpy as np
from typing import Dict, Any, Optional, List

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import torch

logger = logging.getLogger(__name__)

class FunASRService:
    """FunASR语音识别服务类"""

    def __init__(self, model_dir: str = None):
        # 获取项目根目录（语音转文本服务目录）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.model_dir = model_dir or os.path.join(project_root, "models/damo")
        self.asr_pipeline = None
        self.punc_pipeline = None
        self.vad_pipeline = None
        self.is_initialized = False

    async def initialize(self):
        """初始化所有模型"""
        try:
            logger.info("开始初始化FunASR模型...")

            # 检查模型文件是否存在
            asr_model_path = os.path.join(self.model_dir, "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
            punc_model_path = os.path.join(self.model_dir, "punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
            vad_model_path = os.path.join(self.model_dir, "speech_fsmn_vad_zh-cn-16k-common-pytorch")

            if not all(os.path.exists(path) for path in [asr_model_path, punc_model_path, vad_model_path]):
                raise FileNotFoundError("模型文件不存在，请先下载模型")

            # 初始化真实的FunASR模型
            logger.info("开始加载FunASR模型...")

            # 初始化语音识别模型
            self.asr_pipeline = pipeline(
                task=Tasks.auto_speech_recognition,
                model=asr_model_path
            )
            logger.info("语音识别模型加载完成")

            # 初始化标点符号恢复模型
            self.punc_pipeline = pipeline(
                task=Tasks.punctuation,
                model=punc_model_path
            )
            logger.info("标点符号模型加载完成")

            # 初始化VAD模型
            self.vad_pipeline = pipeline(
                task=Tasks.voice_activity_detection,
                model=vad_model_path
            )
            logger.info("VAD模型加载完成")

            self.is_initialized = True
            logger.info("FunASR服务初始化完成")

        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            raise

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

            # 真实语音识别
            logger.info("开始语音识别...")
            asr_result = self.asr_pipeline(temp_file)

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
                    punc_result = self.punc_pipeline(text)
                    if isinstance(punc_result, dict) and 'text' in punc_result:
                        text = punc_result['text']
                except Exception as e:
                    logger.warning(f"标点符号添加失败: {e}")
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
                except:
                    pass

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

    def cleanup(self):
        """清理资源"""
        self.asr_pipeline = None
        self.punc_pipeline = None
        self.vad_pipeline = None
        self.is_initialized = False
        logger.info("FunASR服务资源已清理")

# 创建全局服务实例
funasr_service = FunASRService()