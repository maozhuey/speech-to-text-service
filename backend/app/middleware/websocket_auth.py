"""
WebSocket认证中间件
为WebSocket连接提供简单的令牌认证
"""

import logging
import secrets
import time
import threading
from typing import Optional, Dict
from fastapi import WebSocket, status

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenManager:
    """
    令牌管理器

    管理WebSocket连接的访问令牌，具有以下安全特性：
    - 令牌池大小限制，防止内存耗尽攻击
    - 自动清理过期令牌
    - 令牌唯一性验证
    """

    # 最大令牌池大小（防止DoS攻击）
    MAX_TOKEN_POOL_SIZE = 1000

    def __init__(self, token_expiry: int = 3600, max_pool_size: int = MAX_TOKEN_POOL_SIZE):
        """
        初始化令牌管理器

        Args:
            token_expiry: 令牌过期时间（秒），默认1小时
            max_pool_size: 最大令牌池大小，防止内存耗尽
        """
        self.tokens: Dict[str, float] = {}  # token -> expiry_time
        self.token_expiry = token_expiry
        self.max_pool_size = max_pool_size
        self._lock = threading.Lock()  # 保护令牌池的线程锁

    def generate_token(self) -> str:
        """
        生成新的访问令牌

        使用锁确保线程安全：检查池大小、清理过期令牌、生成新令牌的整个序列是原子的

        Returns:
            str: 32字节的随机令牌

        Raises:
            RuntimeError: 如果令牌池已满
        """
        with self._lock:
            # 检查令牌池是否已满
            if len(self.tokens) >= self.max_pool_size:
                # 先尝试清理过期令牌
                cleaned = self.cleanup_expired()
                if cleaned == 0 and len(self.tokens) >= self.max_pool_size:
                    logger.warning(f"令牌池已满（{self.max_pool_size}），拒绝生成新令牌")
                    raise RuntimeError(f"Token pool is full (max: {self.max_pool_size})")

            token = secrets.token_urlsafe(32)
            expiry = time.time() + self.token_expiry
            self.tokens[token] = expiry
            logger.info(f"生成新令牌，过期时间: {expiry}，当前池大小: {len(self.tokens)}")
            return token

    def validate_token(self, token: str) -> bool:
        """
        验证令牌是否有效

        使用锁保护令牌池访问

        Args:
            token: 要验证的令牌

        Returns:
            bool: 令牌有效返回True，否则返回False
        """
        if not token:
            return False

        with self._lock:
            # 检查令牌是否存在
            if token not in self.tokens:
                logger.warning("拒绝使用无效令牌的连接请求")
                return False

            # 检查令牌是否过期
            expiry = self.tokens[token]
            if time.time() > expiry:
                logger.info("令牌已过期")
                del self.tokens[token]
                return False

            return True

    def revoke_token(self, token: str) -> bool:
        """
        撤销令牌

        使用锁保护令牌池访问

        Args:
            token: 要撤销的令牌

        Returns:
            bool: 成功撤销返回True
        """
        with self._lock:
            if token in self.tokens:
                del self.tokens[token]
                logger.info("已撤销令牌")
                return True
            return False

    def cleanup_expired(self) -> int:
        """
        清理过期的令牌

        使用锁保护令牌池访问

        Returns:
            int: 清理的令牌数量
        """
        with self._lock:
            now = time.time()
            expired_tokens = [
                token for token, expiry in self.tokens.items()
                if now > expiry
            ]

            for token in expired_tokens:
                del self.tokens[token]

            if expired_tokens:
                logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")

            return len(expired_tokens)


# 全局令牌管理器实例
_token_manager = TokenManager(token_expiry=3600)


class WebSocketAuth:
    """
    WebSocket认证处理器

    提供简单的令牌认证机制
    """

    def __init__(self, require_auth: bool = False):
        """
        初始化认证处理器

        Args:
            require_auth: 是否要求认证，False表示仅当提供令牌时验证
        """
        self.require_auth = require_auth

    async def authenticate(self, websocket: WebSocket) -> Optional[Dict]:
        """
        验证WebSocket连接

        Args:
            websocket: WebSocket实例

        Returns:
            认证成功返回用户信息字典，失败返回None
        """
        # 从查询参数获取token
        token = get_token_from_query(websocket)

        # 如果没有提供令牌
        if not token:
            if self.require_auth:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Missing authentication token"
                )
                logger.warning("拒绝未认证的WebSocket连接")
                return None
            else:
                # 可选认证模式：未提供令牌时允许匿名连接
                logger.info("允许匿名WebSocket连接")
                return {"anonymous": True}

        # 验证令牌
        if not _token_manager.validate_token(token):
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired token"
            )
            logger.warning(f"拒绝使用无效令牌的WebSocket连接: {token[:8]}...")
            return None

        logger.info(f"WebSocket连接认证成功: {token[:8]}...")
        return {"authenticated": True, "token": token}


def get_token_from_query(websocket: WebSocket) -> Optional[str]:
    """
    从WebSocket查询参数中提取令牌

    Args:
        websocket: WebSocket实例

    Returns:
        令牌字符串，如果不存在则返回None
    """
    return websocket.query_params.get("token")


def generate_access_token() -> str:
    """
    生成新的访问令牌

    Returns:
        str: 新的访问令牌
    """
    return _token_manager.generate_token()


def validate_access_token(token: str) -> bool:
    """
    验证访问令牌

    Args:
        token: 要验证的令牌

    Returns:
        bool: 令牌有效返回True
    """
    return _token_manager.validate_token(token)


def revoke_access_token(token: str) -> bool:
    """
    撤销访问令牌

    Args:
        token: 要撤销的令牌

    Returns:
        bool: 成功返回True
    """
    return _token_manager.revoke_token(token)
