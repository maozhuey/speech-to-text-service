"""
模型管理器测试

测试 ModelManager 的多模型加载、缓存和资源管理功能。
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from collections import OrderedDict
import tempfile
import os

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.services.model_manager import ModelManager, get_model_manager
from app.core.config import settings


class TestModelManager:
    """模型管理器测试"""

    def test_init(self):
        """测试初始化"""
        manager = ModelManager(max_cached_models=2)
        assert manager.max_cached_models == 2
        assert len(manager.loaded_models) == 0
        assert manager._lock is not None

    def test_singleton(self):
        """测试单例模式"""
        manager1 = get_model_manager(max_cached_models=2)
        manager2 = get_model_manager(max_cached_models=3)
        # 应该返回同一个实例
        assert manager1 is manager2

    @patch('app.services.model_manager.pipeline')
    @patch('os.path.exists')
    def test_load_model_success(self, mock_exists, mock_pipeline):
        """测试成功加载模型"""
        # Mock 文件存在
        mock_exists.return_value = True
        # Mock pipeline 返回值
        mock_pipeline.return_value = Mock()

        manager = ModelManager(max_cached_models=2)
        model_config = {
            "path": "./models/test",
            "type": "offline",
            "enabled": True
        }

        model_dict = manager._load_model("test", "./models/test", model_config)

        assert model_dict is not None
        assert "asr_pipeline" in model_dict
        assert "punc_pipeline" in model_dict
        assert "vad_pipeline" in model_dict

    @patch('app.services.model_manager.pipeline')
    @patch('os.path.exists')
    def test_get_model_cached(self, mock_exists, mock_pipeline):
        """测试从缓存获取模型"""
        mock_exists.return_value = True
        mock_pipeline.return_value = Mock()

        manager = ModelManager(max_cached_models=2)
        model_config = {
            "path": "./models/test",
            "type": "offline",
            "enabled": True
        }

        # 第一次加载
        model1 = manager.get_model("test", model_config)
        # 第二次获取（应该从缓存）
        model2 = manager.get_model("test", model_config)

        assert model1 is model2

    @patch('app.services.model_manager.pipeline')
    @patch('os.path.exists')
    def test_lru_cache_eviction(self, mock_exists, mock_pipeline):
        """测试 LRU 缓存淘汰"""
        mock_exists.return_value = True
        mock_pipeline.return_value = Mock()

        manager = ModelManager(max_cached_models=2)

        model_config1 = {"path": "./models/test1", "type": "offline", "enabled": True}
        model_config2 = {"path": "./models/test2", "type": "offline", "enabled": True}
        model_config3 = {"path": "./models/test3", "type": "offline", "enabled": True}

        # 加载模型1
        manager.get_model("model1", model_config1)
        # 加载模型2
        manager.get_model("model2", model_config2)
        # 访问模型1（更新 LRU）
        manager.get_model("model1", model_config1)
        # 加载模型3（应该淘汰模型2）
        manager.get_model("model3", model_config3)

        # 验证模型2被淘汰
        assert "model1" in manager.loaded_models
        assert "model3" in manager.loaded_models
        assert "model2" not in manager.loaded_models

    def test_get_model_disabled(self):
        """测试禁用的模型"""
        manager = ModelManager(max_cached_models=2)
        model_config = {
            "path": "./models/test",
            "enabled": False
        }

        result = manager.get_model("test", model_config)
        assert result is None

    def test_get_model_no_path(self):
        """测试缺少路径的模型"""
        manager = ModelManager(max_cached_models=2)
        model_config = {
            "enabled": True
        }

        result = manager.get_model("test", model_config)
        assert result is None

    def test_is_model_loaded(self):
        """测试检查模型是否已加载"""
        manager = ModelManager(max_cached_models=2)

        assert not manager.is_model_loaded("test")

        # 手动添加一个模拟的模型
        manager.loaded_models["test"] = {"test": "data"}

        assert manager.is_model_loaded("test")

    def test_get_loaded_models(self):
        """测试获取已加载模型列表"""
        manager = ModelManager(max_cached_models=2)

        assert manager.get_loaded_models() == []

        manager.loaded_models["model1"] = {"test": "data1"}
        manager.loaded_models["model2"] = {"test": "data2"}

        models = manager.get_loaded_models()
        assert "model1" in models
        assert "model2" in models

    @patch('torch.cuda.is_available')
    @patch('gc.collect')
    def test_unload_model(self, mock_gc_collect, mock_cuda_available):
        """测试卸载模型"""
        mock_cuda_available.return_value = False

        manager = ModelManager(max_cached_models=2)
        manager.loaded_models["test"] = {
            "asr_pipeline": Mock(),
            "punc_pipeline": Mock(),
            "vad_pipeline": Mock()
        }

        result = manager._unload_model("test")

        assert result is True
        assert "test" not in manager.loaded_models
        mock_gc_collect.assert_called_once()

    @patch('torch.cuda.is_available')
    @patch('gc.collect')
    def test_cleanup(self, mock_gc_collect, mock_cuda_available):
        """测试清理所有模型"""
        mock_cuda_available.return_value = False

        manager = ModelManager(max_cached_models=2)
        manager.loaded_models["model1"] = {"test": "data1"}
        manager.loaded_models["model2"] = {"test": "data2"}

        manager.cleanup()

        assert len(manager.loaded_models) == 0


class TestConfigModels:
    """配置模型测试"""

    def test_get_models_config(self):
        """测试获取模型配置"""
        models = settings.get_models_config()

        assert isinstance(models, dict)
        assert "offline" in models
        assert "streaming" in models

    def test_offline_model_config(self):
        """测试离线模型配置"""
        models = settings.get_models_config()
        offline = models.get("offline")

        assert offline is not None
        assert offline["name"] == "paraformer-zh-16k-offline"
        assert offline["type"] == "offline"
        assert offline["enabled"] is True
        assert "path" in offline

    def test_streaming_model_config(self):
        """测试流式模型配置"""
        models = settings.get_models_config()
        streaming = models.get("streaming")

        assert streaming is not None
        assert streaming["name"] == "paraformer-zh-streaming"
        assert streaming["type"] == "streaming"
        assert streaming["enabled"] is False  # 默认禁用
        assert "path" in streaming

    def test_get_model_config(self):
        """测试获取单个模型配置"""
        offline = settings.get_model_config("offline")

        assert offline is not None
        assert offline["type"] == "offline"

    def test_get_invalid_model_config(self):
        """测试获取不存在的模型配置"""
        result = settings.get_model_config("invalid")
        assert result is None

    def test_default_model(self):
        """测试默认模型配置"""
        assert settings.default_model == "offline"

    def test_max_cached_models(self):
        """测试最大缓存模型数"""
        assert settings.max_cached_models == 2

    def test_enable_model_switching(self):
        """测试启用模型切换"""
        assert settings.enable_model_switching is True
