"""
限流中间件
用于防止服务被滥用
"""

import time
import logging
import asyncio
from collections import defaultdict
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    简单的内存限流器

    基于滑动窗口算法，限制每个客户端在时间窗口内的请求数
    自动清理过期记录，防止内存泄露
    """

    def __init__(self, max_requests: int = 100, window: int = 60, auto_cleanup_interval: int = 300):
        """
        初始化限流器

        Args:
            max_requests: 时间窗口内最大请求数
            window: 时间窗口（秒）
            auto_cleanup_interval: 自动清理间隔（秒），默认5分钟
        """
        self.max_requests = max_requests
        self.window = window
        self.auto_cleanup_interval = auto_cleanup_interval
        self.requests: Dict[str, list] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_task = None

    def _auto_cleanup_if_needed(self) -> None:
        """如果距离上次清理超过间隔，自动清理过期记录"""
        now = time.time()
        if now - self._last_cleanup > self.auto_cleanup_interval:
            cleaned = self.cleanup_all()
            self._last_cleanup = now
            if cleaned > 0:
                logger.info(f"自动清理了 {cleaned} 条过期请求记录")

    def is_allowed(self, key: str) -> bool:
        """
        检查是否允许请求

        Args:
            key: 客户端标识（如IP地址）

        Returns:
            bool: True表示允许请求，False表示超过限制
        """
        # 定期自动清理
        self._auto_cleanup_if_needed()

        now = time.time()

        # 清理过期记录
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if now - timestamp < self.window
        ]

        # 检查是否超过限制
        if len(self.requests[key]) >= self.max_requests:
            logger.warning(
                f"限流触发: 客户端 {key} 在 {self.window} 秒内"
                f"已发送 {len(self.requests[key])} 个请求"
            )
            return False

        # 记录本次请求
        self.requests[key].append(now)
        return True

    def get_remaining_requests(self, key: str) -> int:
        """
        获取剩余可用请求数

        Args:
            key: 客户端标识

        Returns:
            int: 剩余请求数
        """
        now = time.time()

        # 清理过期记录
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if now - timestamp < self.window
        ]

        return max(0, self.max_requests - len(self.requests[key]))

    def reset(self, key: str) -> None:
        """
        重置指定客户端的请求记录

        Args:
            key: 客户端标识
        """
        if key in self.requests:
            del self.requests[key]
            logger.debug(f"已重置客户端 {key} 的限流记录")

    def cleanup_all(self) -> int:
        """
        清理所有过期的请求记录

        Returns:
            int: 清理的记录数量
        """
        now = time.time()
        total_cleaned = 0

        for key in list(self.requests.keys()):
            original_count = len(self.requests[key])
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp < self.window
            ]
            total_cleaned += original_count - len(self.requests[key])

            # 如果没有活跃请求，删除该key
            if not self.requests[key]:
                del self.requests[key]

        if total_cleaned > 0:
            logger.debug(f"清理了 {total_cleaned} 条过期请求记录")

        return total_cleaned
