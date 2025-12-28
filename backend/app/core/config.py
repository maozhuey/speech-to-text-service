from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
from pydantic import field_validator
import os
import json

class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8002
    max_connections: int = 2

    # CORS安全配置
    allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:8081,http://127.0.0.1:8081,http://localhost:8082,http://127.0.0.1:8082"  # 允许的来源（逗号分隔）
    allowed_methods: str = "GET,POST,OPTIONS"  # 允许的HTTP方法
    allowed_headers: str = "Content-Type,Authorization,Accept,Accept-Language,Content-Language,Origin"  # 允许的请求头

    def get_allowed_origins_list(self) -> List[str]:
        """将允许的来源字符串转换为列表"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def get_allowed_methods_list(self) -> List[str]:
        """将允许的方法字符串转换为列表"""
        return [method.strip() for method in self.allowed_methods.split(",") if method.strip()]

    def get_allowed_headers_list(self) -> List[str]:
        """将允许的请求头字符串转换为列表"""
        return [header.strip() for header in self.allowed_headers.split(",") if header.strip()]

    # ========== 多模型配置 ==========
    # 默认使用的模型
    default_model: str = "offline"

    # 最大缓存的模型数量
    max_cached_models: int = 2

    # 是否启用模型切换功能
    enable_model_switching: bool = True

    # FunASR 模型配置（保留向后兼容，路径相对于 backend 目录）
    model_path: str = "../models/damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_model_path: str = "../models/damo/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    punc_model_path: str = "../models/damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"

    # 流式模型配置（路径相对于 backend 目录）
    streaming_model_path: str = "../models/paraformer-zh-streaming/iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"

    # 模型配置字典（可通过环境变量 MODELS_JSON 覆盖）
    # 格式: JSON字符串，包含各模型的配置信息
    models_json: Optional[str] = None

    def get_models_config(self) -> Dict[str, Dict[str, Any]]:
        """
        获取模型配置字典

        如果环境变量 MODELS_JSON 存在，则解析它；
        否则返回默认配置。
        """
        if self.models_json:
            try:
                return json.loads(self.models_json)
            except (json.JSONDecodeError, TypeError) as e:
                import logging
                logging.warning(f"解析 MODELS_JSON 失败: {e}，使用默认配置")

        # 检测流式模型是否可用
        import os
        streaming_enabled = os.path.exists(self.streaming_model_path)

        # 默认模型配置
        return {
            "offline": {
                "name": "paraformer-zh-16k-offline",
                "display_name": "离线模型（高精度）",
                "path": self.model_path,
                "type": "offline",
                "description": "适合会议记录、文档转录，延迟5-10秒",
                "enabled": True
            },
            "streaming": {
                "name": "paraformer-zh-streaming",
                "display_name": "流式模型（低延迟）",
                "path": self.streaming_model_path,
                "type": "streaming",
                "description": "适合语音输入、实时字幕，延迟<300ms",
                "enabled": streaming_enabled  # 自动检测是否可用
            }
        }

    def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模型的配置

        Args:
            model_name: 模型名称（offline 或 streaming）

        Returns:
            模型配置字典，如果模型不存在则返回 None
        """
        models = self.get_models_config()
        return models.get(model_name)

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

    # 安全配置
    require_extended_health_auth: bool = True  # 是否要求扩展健康检查提供认证令牌
    max_cleanup_queue_size: int = 1000  # 最大临时文件清理队列大小（防止内存耗尽）

    @field_validator('max_cleanup_queue_size')
    @classmethod
    def validate_max_cleanup_queue_size(cls, v: int) -> int:
        """验证max_cleanup_queue_size在合理范围内"""
        if v < 100:
            raise ValueError('max_cleanup_queue_size must be at least 100')
        if v > 10000:
            raise ValueError('max_cleanup_queue_size must not exceed 10000')
        return v

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }

# 创建全局配置实例
settings = Settings()