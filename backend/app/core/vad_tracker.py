"""VAD状态跟踪器模块"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class VADStateTracker:
    """跟踪单个WebSocket连接的VAD状态，用于智能断句"""

    def __init__(
        self,
        silence_threshold_ms: int = 800,
        max_segment_duration_ms: int = 20000,
        sample_rate: int = 16000
    ):
        """
        初始化VAD状态跟踪器

        Args:
            silence_threshold_ms: 连续静音时长阈值（毫秒），超过此值触发断句
            max_segment_duration_ms: 单段最大时长（毫秒），防止过长不断句
            sample_rate: 音频采样率，用于计算音频块时长
        """
        self.silence_threshold_ms = silence_threshold_ms
        self.max_segment_duration_ms = max_segment_duration_ms
        self.sample_rate = sample_rate

        # 状态变量
        self.consecutive_silence_ms = 0.0  # 连续静音时长（毫秒）
        self.total_segment_duration_ms = 0.0  # 当前段总时长（毫秒）
        self.last_speech_time: Optional[float] = None  # 上次检测到语音的时间

    def process_audio_chunk(self, has_speech: bool, audio_size_bytes: int) -> bool:
        """
        处理音频块，返回是否应该触发断句

        Args:
            has_speech: VAD检测结果，True表示包含语音
            audio_size_bytes: 音频数据大小（字节），16位PCM格式

        Returns:
            bool: 是否应该触发断句
        """
        # 计算音频块时长（毫秒）
        # 16位PCM = 2字节/采样，16kHz采样率
        chunk_duration_ms = (audio_size_bytes / 2) / self.sample_rate * 1000

        if has_speech:
            # 检测到语音
            self.consecutive_silence_ms = 0
            self.total_segment_duration_ms += chunk_duration_ms
            self.last_speech_time = time.time()

            # 检查是否超过最大时长
            if self.total_segment_duration_ms >= self.max_segment_duration_ms:
                logger.info(f"VAD: 达到最大段时长 {self.total_segment_duration_ms:.0f}ms，触发断句")
                return True

            return False
        else:
            # 检测到静音
            self.consecutive_silence_ms += chunk_duration_ms

            # 检查是否达到静音阈值
            if self.consecutive_silence_ms >= self.silence_threshold_ms:
                # 只有当累积了一些音频后才触发断句（避免开头静音触发）
                if self.total_segment_duration_ms > 100:  # 至少100ms的语音
                    logger.info(
                        f"VAD: 检测到 {self.consecutive_silence_ms:.0f}ms 静音，"
                        f"触发断句（段时长: {self.total_segment_duration_ms:.0f}ms）"
                    )
                    return True

            return False

    def reset(self):
        """重置VAD状态，用于开始新的音频段"""
        self.consecutive_silence_ms = 0.0
        self.total_segment_duration_ms = 0.0
        self.last_speech_time = None

    def get_state(self) -> dict:
        """
        获取当前VAD状态

        Returns:
            dict: 包含当前状态的字典
        """
        return {
            "consecutive_silence_ms": self.consecutive_silence_ms,
            "total_segment_duration_ms": self.total_segment_duration_ms,
            "silence_threshold_ms": self.silence_threshold_ms,
            "max_segment_duration_ms": self.max_segment_duration_ms,
            "has_speech_recently": self.consecutive_silence_ms < 500
        }
