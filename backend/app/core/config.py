from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8002
    max_connections: int = 2

    # FunASR模型配置
    model_path: str = "./models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_model_path: str = "./models/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    punc_model_path: str = "./models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"

    # 音频配置
    sample_rate: int = 16000
    audio_chunk_size: int = 1024
    max_audio_length: int = 30  # 秒

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # 环境配置
    debug: bool = False

    # VAD断句配置
    vad_silence_threshold_ms: int = 800  # 连续静音时长阈值（毫秒）
    vad_max_segment_duration_ms: int = 20000  # 单段最大时长（毫秒）
    vad_enabled: bool = True  # 是否启用VAD断句

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }

# 创建全局配置实例
settings = Settings()