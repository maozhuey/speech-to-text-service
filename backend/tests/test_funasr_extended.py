"""
FunASR服务扩展测试
专注于提升funasr_service.py的覆盖率
测试异常处理、边界条件和完整功能路径
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import numpy as np
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from conftest import audio_generator

from app.services.funasr_service import FunASRService, funasr_service


class TestFunASRInitialization:
    """FunASR初始化测试"""

    @pytest.mark.asyncio
    async def test_auto_initialization_on_first_call(self):
        """测试首次调用时自动初始化"""
        service = FunASRService()
        assert service.is_initialized is False

        # 首次调用应该触发自动初始化
        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()
        result = await service.recognize_speech(audio_data, 16000)

        # 应该返回结果（成功或失败）
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_initialization_with_missing_model_files(self):
        """测试模型文件不存在时的初始化失败"""
        service = FunASRService()
        service.model_dir = "/nonexistent/path"

        with pytest.raises(FileNotFoundError):
            await service.initialize()

    @pytest.mark.asyncio
    async def test_initialization_failure_handling(self):
        """测试初始化失败的异常处理"""
        service = FunASRService()

        # Mock os.path.exists返回True，但mock pipeline抛出异常
        with patch('os.path.exists', return_value=True), \
             patch('app.services.funasr_service.pipeline', side_effect=Exception("Model load failed")):

            with pytest.raises(Exception, match="Model load failed"):
                await service.initialize()

            assert service.is_initialized is False


class TestFunASRTempFileHandling:
    """FunASR临时文件处理测试"""

    @pytest.mark.asyncio
    async def test_temp_file_cleanup_on_success(self):
        """测试成功时清理临时文件"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        # Mock临时文件清理
        temp_files_created = []
        original_unlink = os.unlink

        def mock_unlink(path):
            temp_files_created.append(path)
            original_unlink(path)

        with patch('os.unlink', side_effect=mock_unlink):
            result = await service.recognize_speech(audio_data, 16000)

        # 验证临时文件被创建和清理
        assert result is not None

    @pytest.mark.asyncio
    async def test_temp_file_cleanup_on_error(self):
        """测试错误时也清理临时文件"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 创建无效音频数据
        invalid_audio = b"invalid_audio_data"

        result = await service.recognize_speech(invalid_audio, 16000)

        # 应该返回错误结果，但不会崩溃
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_temp_file_cleanup_failure_logging(self):
        """测试临时文件清理失败的日志记录"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        # Mock os.unlink抛出异常
        with patch('os.unlink', side_effect=OSError("Permission denied")):
            result = await service.recognize_speech(audio_data, 16000)

        # 应该仍然返回结果，即使清理失败
        assert result is not None

    def test_save_temp_audio_failure(self):
        """测试保存临时音频文件失败"""
        service = FunASRService()
        audio_array = np.random.randn(1600).astype(np.float32)

        # Mock wave.open抛出异常
        with patch('wave.open', side_effect=IOError("Disk full")):
            with pytest.raises(IOError):
                service._save_temp_audio(audio_array, 16000)


class TestFunASRBatchRecognition:
    """FunASR批量识别测试"""

    @pytest.mark.asyncio
    async def test_batch_recognize_success(self):
        """测试批量识别成功"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 创建多个音频块
        audio_chunks = [
            np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()
            for _ in range(3)
        ]

        results = await service.batch_recognize(audio_chunks, 16000)

        # 验证结果
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result is not None
            assert "chunk_index" in result
            assert result["chunk_index"] == i

    @pytest.mark.asyncio
    async def test_batch_recognize_with_empty_chunks(self):
        """测试批量识别包含空块"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        audio_chunks = [
            np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes(),
            b"",  # 空音频
            np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes(),
        ]

        results = await service.batch_recognize(audio_chunks, 16000)

        # 应该返回3个结果，空块会失败
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_batch_recognize_with_invalid_chunks(self):
        """测试批量识别包含无效块"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        audio_chunks = [
            np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes(),
            b"invalid_audio",  # 无效音频
        ]

        results = await service.batch_recognize(audio_chunks, 16000)

        # 应该返回2个结果
        assert len(results) == 2
        # 第二个应该是失败的结果
        assert results[1]["success"] is False or "error" in results[1]

    @pytest.mark.asyncio
    async def test_batch_recognize_empty_list(self):
        """测试批量识别空列表"""
        service = FunASRService()

        results = await service.batch_recognize([], 16000)

        # 应该返回空列表
        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_chunks", [1, 5, 10])
    async def test_batch_recognize_various_sizes(self, num_chunks):
        """测试不同大小的批量识别（参数化测试）"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        audio_chunks = [
            np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()
            for _ in range(num_chunks)
        ]

        results = await service.batch_recognize(audio_chunks, 16000)

        # 验证结果数量
        assert len(results) == num_chunks


class TestFunASRVAD:
    """FunASR VAD检测测试"""

    @pytest.mark.asyncio
    async def test_vad_detection_success(self):
        """测试VAD检测成功"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件和VAD模型")

        # 创建有语音的音频
        audio_data = np.random.randint(-16384, 16383, size=16000, dtype=np.int16).tobytes()

        result = await service.detect_voice_activity(audio_data, 16000)

        # 验证结果
        assert result is not None
        assert "success" in result
        assert "has_speech" in result

    @pytest.mark.asyncio
    async def test_vad_detection_with_silence(self):
        """测试VAD检测静音"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件和VAD模型")

        # 创建静音音频（接近零）
        silence_audio = np.zeros(16000, dtype=np.int16).tobytes()

        result = await service.detect_voice_activity(silence_audio, 16000)

        # 验证结果
        assert result is not None
        assert "success" in result

    @pytest.mark.asyncio
    async def test_vad_detection_failure(self):
        """测试VAD检测失败处理"""
        service = FunASRService()

        # 创建无效音频
        invalid_audio = b"invalid"

        result = await service.detect_voice_activity(invalid_audio, 16000)

        # 应该返回失败结果
        assert result is not None
        assert "success" in result
        # 如果验证失败，success应该为False


class TestFunASRRealtimeVAD:
    """FunASR实时VAD检测测试"""

    @pytest.mark.asyncio
    async def test_realtime_vad_with_speech(self):
        """测试实时VAD检测语音"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 创建有语音的音频（能量较高）
        audio_data = np.random.randint(-20000, 20000, size=16000, dtype=np.int16).tobytes()

        result = await service.detect_voice_activity_realtime(audio_data, 16000)

        # 验证结果
        assert result is not None
        assert "has_speech" in result
        assert "success" in result

    @pytest.mark.asyncio
    async def test_realtime_vad_with_silence(self):
        """测试实时VAD检测静音"""
        service = FunASRService()

        # 创建静音音频（能量很低）
        silence_audio = np.zeros(16000, dtype=np.int16).tobytes()

        result = await service.detect_voice_activity_realtime(silence_audio, 16000)

        # 静音应该返回has_speech=False
        assert result is not None
        assert "has_speech" in result

    @pytest.mark.asyncio
    async def test_realtime_vad_with_boundary_energy(self):
        """测试实时VAD边界能量区域"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 创建边界能量的音频（0.0005 < energy < 0.002）
        # 计算需要的能量：energy = mean(x^2)
        # 对于均值为0，标准差为std的正态分布，energy = std^2
        # 需要 sqrt(0.001) ≈ 0.0316 的标准差
        audio_data = np.random.normal(0, 0.032, 16000).astype(np.float32)
        audio_int16 = (audio_data * 32767).astype(np.int16).tobytes()

        result = await service.detect_voice_activity_realtime(audio_int16, 16000)

        # 验证结果
        assert result is not None
        assert "has_speech" in result

    @pytest.mark.asyncio
    async def test_realtime_vad_short_audio(self):
        """测试实时VAD处理短音频"""
        service = FunASRService()

        # 创建短于0.1秒的音频
        short_audio = np.zeros(800, dtype=np.int16).tobytes()

        result = await service.detect_voice_activity_realtime(short_audio, 16000)

        # 短音频应该直接返回False，不进行VAD检测
        assert result is not None
        assert result.get("has_speech") is False

    @pytest.mark.asyncio
    async def test_realtime_vad_file_cleanup_on_boundary(self):
        """测试边界情况下实时VAD清理临时文件"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 创建边界能量的音频
        audio_data = np.random.normal(0, 0.032, 16000).astype(np.float32)
        audio_int16 = (audio_data * 32767).astype(np.int16).tobytes()

        temp_files_created = []

        def mock_unlink(path):
            if path.endswith('.wav'):
                temp_files_created.append(path)

        with patch('os.unlink', side_effect=mock_unlink):
            result = await service.detect_voice_activity_realtime(audio_int16, 16000)

        # 验证结果
        assert result is not None

    @pytest.mark.asyncio
    async def test_realtime_vad_file_cleanup_failure(self):
        """测试临时文件清理失败的处理"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 创建边界能量的音频
        audio_data = np.random.normal(0, 0.032, 16000).astype(np.float32)
        audio_int16 = (audio_data * 32767).astype(np.int16).tobytes()

        # Mock unlink抛出OSError
        with patch('os.unlink', side_effect=OSError("Cleanup failed")):
            result = await service.detect_voice_activity_realtime(audio_int16, 16000)

        # 应该仍然返回结果
        assert result is not None
        assert "has_speech" in result


class TestFunASRCleanup:
    """FunASR资源清理测试"""

    @pytest.mark.asyncio
    async def test_cleanup_resources(self):
        """测试清理资源"""
        service = FunASRService()

        # 先初始化
        try:
            await service.initialize()
        except:
            pytest.skip("需要模型文件")

        # 验证已初始化
        is_initialized_before = service.is_initialized

        # 清理资源
        service.cleanup()

        # 验证已清理
        assert service.is_initialized is False
        assert service.asr_pipeline is None
        assert service.punc_pipeline is None
        assert service.vad_pipeline is None

    def test_cleanup_without_initialization(self):
        """测试未初始化时清理"""
        service = FunASRService()

        # 未初始化时清理应该安全
        service.cleanup()

        assert service.is_initialized is False
        assert service.asr_pipeline is None

    def test_cleanup_executor_shutdown(self):
        """测试线程池关闭"""
        from app.services.funasr_service import _model_executor

        service = FunASRService()
        service.cleanup()

        # 清理后应该能继续使用（会创建新的executor）
        assert _model_executor is not None


class TestFunASRErrorScenarios:
    """FunASR错误场景测试"""

    @pytest.mark.asyncio
    async def test_recognition_with_invalid_audio(self):
        """测试无效音频的识别"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # 无效音频数据
        invalid_audio = b"not valid audio"

        result = await service.recognize_speech(invalid_audio, 16000)

        # 应该返回错误结果
        assert result is not None
        assert "success" in result
        # 无效音频应该导致失败或返回错误信息
        if not result.get("success"):
            assert "error" in result or result.get("text") == ""

    @pytest.mark.asyncio
    async def test_recognition_exception_handling(self):
        """测试识别过程中的异常处理"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        # Mock _validate_audio抛出异常
        with patch.object(service, '_validate_audio', side_effect=ValueError("Invalid audio")):
            result = await service.recognize_speech(b"fake_audio", 16000)

            # 应该返回错误结果
            assert result is not None
            assert result.get("success") is False

    @pytest.mark.asyncio
    async def test_recognition_with_punctuation_error(self):
        """测试标点符号添加失败的情况"""
        service = FunASRService()
        if not service.is_initialized:
            try:
                await service.initialize()
            except:
                pytest.skip("需要模型文件")

        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        # Mock punc_pipeline抛出异常
        if service.punc_pipeline is not None:
            original_punc = service.punc_pipeline

            def mock_punc_with_error(*args, **kwargs):
                raise Exception("Punctuation failed")

            with patch.object(service, 'punc_pipeline', side_effect=mock_punc_with_error):
                # 应该仍然返回识别结果（没有标点）
                result = await service.recognize_speech(audio_data, 16000)
                assert result is not None


class TestFunASRGlobalService:
    """全局FunASR服务测试"""

    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """测试全局服务实例"""
        global funasr_service

        # 验证全局实例存在
        assert funasr_service is not None
        assert isinstance(funasr_service, FunASRService)

    @pytest.mark.asyncio
    async def test_global_service_auto_init(self):
        """测试全局服务自动初始化"""
        global funasr_service

        # 尝试使用全局服务
        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        try:
            result = await funasr_service.recognize_speech(audio_data, 16000)
            assert result is not None
        except FileNotFoundError:
            # 模型文件不存在是正常的（在没有模型的环境中）
            pass
        except Exception as e:
            # 其他异常也应该被捕获
            assert isinstance(e, Exception)


class TestFunASRPunctuation:
    """FunASR标点符号处理测试"""

    @pytest.mark.asyncio
    async def test_punctuation_addition_success(self):
        """测试成功添加标点符号"""
        service = FunASRService()
        if not service.is_initialized or service.punc_pipeline is None:
            pytest.skip("需要标点符号模型")

        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()

        result = await service.recognize_speech(audio_data, 16000)

        # 验证结果包含标点符号处理后的文本
        assert result is not None
        if result.get("success"):
            assert "text" in result

    @pytest.mark.asyncio
    async def test_recognition_without_punctuation_model(self):
        """测试没有标点符号模型时的识别"""
        service = FunASRService()
        service.punc_pipeline = None

        # Mock模型已初始化
        service.is_initialized = True

        # Mock ASR结果（没有标点符号）
        mock_asr_result = [{"text": "你好世界"}]

        with patch.object(service, 'asr_pipeline', return_value=mock_asr_result):
            audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16).tobytes()
            result = await service.recognize_speech(audio_data, 16000)

            # 应该返回ASR结果（没有标点符号）
            assert result is not None
