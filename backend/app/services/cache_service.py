"""
Redis缓存服务
用于缓存CMS API获取的流URL，减少重复请求
"""

import json
from typing import Optional, Any
import redis.asyncio as redis
from app.utils.logger import logger
from app.utils.exceptions import CacheException
from app.config import settings


class CacheService:
    """Redis缓存服务类"""

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化缓存服务

        Args:
            redis_url: Redis连接URL，默认使用配置中的值
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.client: Optional[redis.Redis] = None
        self.enabled = True

    async def connect(self):
        """连接Redis"""
        if not self.enabled:
            logger.warning("Redis缓存已禁用")
            return

        try:
            self.client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.client.ping()
            logger.info(f"Redis缓存服务已连接: {self.redis_url}")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            logger.warning("缓存功能将不可用，但不影响主流程")
            self.enabled = False
            self.client = None

    async def disconnect(self):
        """断开Redis连接"""
        if self.client:
            await self.client.close()
            logger.info("Redis缓存服务已断开")

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回None
        """
        if not self.enabled or not self.client:
            return None

        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒），默认1小时

        Returns:
            bool: 成功返回True，失败返回False
        """
        if not self.enabled or not self.client:
            return False

        try:
            await self.client.set(key, json.dumps(value), ex=expire)
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            bool: 成功返回True，失败返回False
        """
        if not self.enabled or not self.client:
            return False

        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            bool: 存在返回True，不存在返回False
        """
        if not self.enabled or not self.client:
            return False

        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {e}")
            return False

    async def get_stream_url(self, token: str, camera_id: str) -> Optional[Dict]:
        """
        获取缓存的播放URL

        Args:
            token: Bearer Token
            camera_id: 摄像头ID

        Returns:
            Dict: 缓存的URL信息，不存在返回None
        """
        import hashlib

        cache_key = self._generate_stream_url_key(token, camera_id)
        return await self.get(cache_key)

    async def set_stream_url(
        self, token: str, camera_id: str, url_data: Dict, expire: int = 6220800
    ) -> bool:
        """
        缓存播放URL

        Args:
            token: Bearer Token
            camera_id: 摄像头ID
            url_data: URL数据
            expire: 过期时间（秒），默认72天

        Returns:
            bool: 成功返回True，失败返回False
        """
        cache_key = self._generate_stream_url_key(token, camera_id)
        return await self.set(cache_key, url_data, expire)

    def _generate_stream_url_key(self, token: str, camera_id: str) -> str:
        """
        生成播放URL的缓存键

        Args:
            token: Bearer Token
            camera_id: 摄像头ID

        Returns:
            str: 缓存键
        """
        import hashlib

        key_data = f"{token}:{camera_id}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"stream_url:{key_hash}"

    async def invalidate_stream_url(self, token: str, camera_id: str) -> bool:
        """
        使缓存的播放URL失效

        Args:
            token: Bearer Token
            camera_id: 摄像头ID

        Returns:
            bool: 成功返回True，失败返回False
        """
        cache_key = self._generate_stream_url_key(token, camera_id)
        return await self.delete(cache_key)
