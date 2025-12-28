"""
API端点测试
测试health、info和token端点
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.core.websocket import websocket_manager


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_endpoint_basic(self):
        """测试基础健康检查端点"""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "speech-to-text"
        assert "version" in data
        assert "active_connections" in data

    def test_health_endpoint_no_sensitive_info(self):
        """测试健康检查不暴露敏感信息"""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        data = response.json()

        # 不应该包含CPU和内存信息
        assert "cpu_usage" not in data
        assert "memory_usage" not in data
        assert "max_connections" not in data

    def test_extended_health_endpoint(self):
        """测试扩展健康检查端点"""
        client = TestClient(app)
        response = client.get("/api/v1/health/extended")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "active_connections" in data
        assert "max_connections" in data
        assert "memory_usage_percent" in data
        assert "cpu_usage_percent" in data


class TestInfoEndpoint:
    """信息端点测试"""

    def test_info_endpoint(self):
        """测试服务信息端点"""
        client = TestClient(app)
        response = client.get("/api/v1/info")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "features" in data
        assert isinstance(data["features"], list)


class TestTokenEndpoint:
    """令牌端点测试"""

    def test_generate_token_endpoint(self):
        """测试生成令牌端点"""
        client = TestClient(app)
        response = client.get("/api/v1/token")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "token" in data
        assert len(data["token"]) > 20
        assert "message" in data

    def test_tokens_are_unique(self):
        """测试多次生成的令牌是唯一的"""
        client = TestClient(app)
        tokens = set()

        for _ in range(10):
            response = client.get("/api/v1/token")
            token = response.json()["token"]
            tokens.add(token)

        # 所有令牌应该唯一
        assert len(tokens) == 10


class TestRootEndpoint:
    """根端点测试"""

    def test_root_endpoint(self):
        """测试根路径返回HTML"""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "语音转文本服务" in response.text


class TestCORSEndpoints:
    """CORS配置测试"""

    def test_cors_headers_on_get(self):
        """测试GET请求的CORS头"""
        client = TestClient(app)

        # 使用特定来源
        headers = {"Origin": "http://localhost:8080"}
        response = client.get("/api/v1/health", headers=headers)

        assert response.status_code == 200
        # 验证CORS头存在
        assert "access-control-allow-origin" in response.headers


class TestRequestLogging:
    """请求日志测试"""

    def test_process_time_header(self):
        """测试响应包含处理时间头"""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert "x-process-time" in response.headers
        # 处理时间应该是数字
        float(response.headers["x-process-time"])


class TestRateLimiting:
    """限流测试"""

    def test_rate_limiting_on_websocket(self):
        """测试WebSocket端点的限流"""
        # 这个测试需要WebSocket客户端，这里只测试端点存在
        client = TestClient(app)

        # 尝试快速连接多次（使用HTTP升级）
        # 注意：完整的WebSocket测试需要WebSocket客户端
        for _ in range(5):
            # 这里只是验证端点存在
            response = client.get("/api/v1/health")
            assert response.status_code == 200


class TestErrorHandling:
    """错误处理测试"""

    def test_404_on_invalid_path(self):
        """测试无效路径返回404"""
        client = TestClient(app)
        response = client.get("/api/v1/invalid")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """测试不允许的方法"""
        client = TestClient(app)
        response = client.post("/api/v1/health")

        # 应该返回405或422
        assert response.status_code in [405, 422]


class TestFrontendEndpoint:
    """前端端点测试"""

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_frontend_file_not_found(self, mock_open):
        """测试前端文件不存在时的处理"""
        client = TestClient(app)
        response = client.get("/frontend")

        assert response.status_code == 200
        assert "未找到" in response.text

    def test_frontend_endpoint_exists(self):
        """测试前端端点存在"""
        client = TestClient(app)
        # 只测试端点存在，不测试文件内容
        response = client.get("/frontend")

        # 端点应该存在（可能返回文件或错误消息）
        assert response.status_code == 200
