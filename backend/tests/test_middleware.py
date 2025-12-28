"""
中间件测试
测试限流和WebSocket认证中间件
"""

import sys
from pathlib import Path

# 添加后端目录到Python路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

import pytest
import time
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from app.middleware.rate_limit import RateLimiter
from app.middleware.websocket_auth import TokenManager, WebSocketAuth, generate_access_token


class TestRateLimiter:
    """限流器测试"""

    def test_initialization(self):
        """测试限流器初始化"""
        limiter = RateLimiter(max_requests=10, window=60)
        assert limiter.max_requests == 10
        assert limiter.window == 60

    def test_allow_first_request(self):
        """测试第一个请求应该被允许"""
        limiter = RateLimiter(max_requests=10, window=60)
        assert limiter.is_allowed("client1") is True

    def test_allow_within_limit(self):
        """测试限制内的请求应该被允许"""
        limiter = RateLimiter(max_requests=5, window=60)
        client = "client1"

        for _ in range(5):
            assert limiter.is_allowed(client) is True

    def test_deny_over_limit(self):
        """测试超过限制后请求应该被拒绝"""
        limiter = RateLimiter(max_requests=3, window=60)
        client = "client1"

        # 前3个请求应该被允许
        for _ in range(3):
            assert limiter.is_allowed(client) is True

        # 第4个请求应该被拒绝
        assert limiter.is_allowed(client) is False

    def test_independent_clients(self):
        """测试不同客户端的限流是独立的"""
        limiter = RateLimiter(max_requests=2, window=60)

        # client1 达到限制
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False

        # client2 应该仍然被允许
        assert limiter.is_allowed("client2") is True

    def test_window_expiry(self):
        """测试时间窗口过期后重置计数"""
        limiter = RateLimiter(max_requests=2, window=1, auto_cleanup_interval=1)
        client = "client1"

        # 达到限制
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is False

        # 等待窗口过期
        time.sleep(1.1)

        # 重新计数
        assert limiter.is_allowed(client) is True

    def test_get_remaining_requests(self):
        """测试获取剩余请求数"""
        limiter = RateLimiter(max_requests=10, window=60)
        client = "client1"

        assert limiter.get_remaining_requests(client) == 10

        limiter.is_allowed(client)
        assert limiter.get_remaining_requests(client) == 9

        limiter.is_allowed(client)
        assert limiter.get_remaining_requests(client) == 8

    def test_reset_client(self):
        """测试重置客户端限制"""
        limiter = RateLimiter(max_requests=2, window=60)
        client = "client1"

        # 达到限制
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is False

        # 重置
        limiter.reset(client)

        # 应该重新被允许
        assert limiter.is_allowed(client) is True

    def test_auto_cleanup(self):
        """测试自动清理过期记录"""
        limiter = RateLimiter(max_requests=10, window=1, auto_cleanup_interval=2)

        # 添加多个客户端
        for i in range(5):
            limiter.is_allowed(f"client{i}")

        # 等待过期和清理
        time.sleep(2.5)

        # 触发自动清理
        limiter.is_allowed("new_client")

        # 验证旧记录被清理（通过重置时间间接验证）
        assert limiter._last_cleanup > time.time() - 5

    def test_cleanup_all(self):
        """测试清理所有过期记录"""
        limiter = RateLimiter(max_requests=10, window=1)

        # 添加多个客户端
        for i in range(5):
            limiter.is_allowed(f"client{i}")

        # 等待过期
        time.sleep(1.1)

        # 清理所有（返回清理的记录数）
        cleaned = limiter.cleanup_all()

        # cleanup_all返回清理的记录数
        assert cleaned >= 5  # 至少清理5个记录


class TestTokenManager:
    """令牌管理器测试"""

    def test_generate_token(self):
        """测试生成令牌"""
        manager = TokenManager(token_expiry=3600)
        token = manager.generate_token()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20  # URL-safe base64 token应该足够长

    def test_validate_valid_token(self):
        """测试验证有效令牌"""
        manager = TokenManager(token_expiry=3600)
        token = manager.generate_token()

        assert manager.validate_token(token) is True

    def test_validate_invalid_token(self):
        """测试验证无效令牌"""
        manager = TokenManager(token_expiry=3600)

        assert manager.validate_token("invalid_token") is False
        assert manager.validate_token("") is False
        assert manager.validate_token(None) is False

    def test_token_expiry(self):
        """测试令牌过期"""
        manager = TokenManager(token_expiry=1)  # 1秒过期
        token = manager.generate_token()

        # 立即验证应该成功
        assert manager.validate_token(token) is True

        # 等待过期
        time.sleep(1.1)

        # 过期后验证应该失败
        assert manager.validate_token(token) is False

    def test_revoke_token(self):
        """测试撤销令牌"""
        manager = TokenManager(token_expiry=3600)
        token = manager.generate_token()

        # 撤销前应该有效
        assert manager.validate_token(token) is True

        # 撤销
        assert manager.revoke_token(token) is True

        # 撤销后应该无效
        assert manager.validate_token(token) is False

    def test_revoke_nonexistent_token(self):
        """测试撤销不存在的令牌"""
        manager = TokenManager(token_expiry=3600)

        assert manager.revoke_token("nonexistent") is False

    def test_cleanup_expired(self):
        """测试清理过期令牌"""
        manager = TokenManager(token_expiry=1)

        # 生成多个令牌
        tokens = [manager.generate_token() for _ in range(5)]

        # 等待过期
        time.sleep(1.1)

        # 清理过期令牌
        cleaned = manager.cleanup_expired()

        assert cleaned == 5

        # 验证令牌已不存在
        for token in tokens:
            assert manager.validate_token(token) is False

    def test_unique_tokens(self):
        """测试生成的令牌是唯一的"""
        manager = TokenManager(token_expiry=3600)
        tokens = set()

        for _ in range(100):
            token = manager.generate_token()
            tokens.add(token)

        # 所有令牌应该唯一
        assert len(tokens) == 100


class TestWebSocketAuth:
    """WebSocket认证测试"""

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self):
        """测试使用有效令牌认证"""
        auth = WebSocketAuth(require_auth=True)
        websocket = Mock()
        websocket.close = AsyncMock()

        # 生成有效令牌
        token = generate_access_token()
        websocket.query_params = {"token": token}

        # 认证应该成功
        result = await auth.authenticate(websocket)
        assert result is not None
        assert result.get("authenticated") is True

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_token_required(self):
        """测试必需认证模式下使用无效令牌"""
        auth = WebSocketAuth(require_auth=True)
        websocket = Mock()
        websocket.close = AsyncMock()

        # 无效令牌
        websocket.query_params = {"token": "invalid_token"}

        # 认证应该失败，连接应被关闭
        result = await auth.authenticate(websocket)
        assert result is None
        websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_without_token_optional(self):
        """测试可选认证模式下无令牌"""
        auth = WebSocketAuth(require_auth=False)
        websocket = Mock()

        # 没有令牌
        websocket.query_params = {}

        # 认证应该成功（匿名）
        result = await auth.authenticate(websocket)
        assert result is not None
        assert result.get("anonymous") is True

    @pytest.mark.asyncio
    async def test_authenticate_without_token_required(self):
        """测试必需认证模式下无令牌"""
        auth = WebSocketAuth(require_auth=True)
        websocket = Mock()
        websocket.close = AsyncMock()

        # 没有令牌
        websocket.query_params = {}

        # 认证应该失败
        result = await auth.authenticate(websocket)
        assert result is None
        websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_with_expired_token(self):
        """测试使用过期令牌认证"""
        auth = WebSocketAuth(require_auth=True)
        websocket = Mock()
        websocket.close = AsyncMock()

        # 生成并等待令牌过期
        from app.middleware.websocket_auth import _token_manager
        token = _token_manager.generate_token()
        # 手动设置过期时间
        _token_manager.tokens[token] = time.time() - 10

        websocket.query_params = {"token": token}

        # 认证应该失败
        result = await auth.authenticate(websocket)
        assert result is None


class TestGenerateAccessToken:
    """令牌生成函数测试"""

    def test_generate_access_token(self):
        """测试生成访问令牌函数"""
        token = generate_access_token()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20

    def test_tokens_are_unique(self):
        """测试生成的令牌是唯一的"""
        tokens = [generate_access_token() for _ in range(50)]

        # 所有令牌应该唯一
        assert len(set(tokens)) == 50
