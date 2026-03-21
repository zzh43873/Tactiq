"""
Redis客户端封装
用于任务状态存储和缓存
"""

import json
import pickle
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID
import redis.asyncio as redis
from app.config import settings
from loguru import logger


class RedisClient:
    """Redis客户端单例类"""
    
    _instance: Optional['RedisClient'] = None
    _redis: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """连接Redis"""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis.ping()
                logger.info("Redis connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis
    
    async def disconnect(self):
        """断开Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis disconnected")
    
    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis


# 全局Redis客户端实例
redis_client = RedisClient()


class TaskStorage:
    """
    任务状态存储
    使用Redis持久化任务状态，支持服务重启后恢复
    """
    
    KEY_PREFIX = "tactiq:task:"
    TTL = 86400 * 7  # 7天过期
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """获取Redis连接"""
        if self._redis is None:
            self._redis = await redis_client.connect()
        return self._redis
    
    def _make_key(self, task_type: str, task_id: str) -> str:
        """生成Redis键"""
        return f"{self.KEY_PREFIX}{task_type}:{task_id}"
    
    async def save_task(self, task_type: str, task_id: str, data: Dict[str, Any]):
        """
        保存任务状态
        
        Args:
            task_type: 任务类型 (intelligence/simulation)
            task_id: 任务ID
            data: 任务数据
        """
        try:
            r = await self._get_redis()
            key = self._make_key(task_type, task_id)
            
            # 序列化数据（处理datetime等类型）
            serialized = json.dumps(data, default=self._json_serializer)
            
            await r.setex(key, self.TTL, serialized)
            logger.debug(f"Task saved: {key}")
        except Exception as e:
            logger.error(f"Failed to save task {task_id}: {e}")
            raise
    
    async def get_task(self, task_type: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_type: 任务类型
            task_id: 任务ID
            
        Returns:
            任务数据，不存在则返回None
        """
        try:
            r = await self._get_redis()
            key = self._make_key(task_type, task_id)
            
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def update_task(self, task_type: str, task_id: str, updates: Dict[str, Any]):
        """
        更新任务状态（合并更新）
        
        Args:
            task_type: 任务类型
            task_id: 任务ID
            updates: 更新的字段
        """
        try:
            existing = await self.get_task(task_type, task_id)
            if existing:
                existing.update(updates)
                await self.save_task(task_type, task_id, existing)
            else:
                await self.save_task(task_type, task_id, updates)
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise
    
    async def delete_task(self, task_type: str, task_id: str):
        """删除任务"""
        try:
            r = await self._get_redis()
            key = self._make_key(task_type, task_id)
            await r.delete(key)
            logger.debug(f"Task deleted: {key}")
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
    
    async def list_tasks(self, task_type: str, limit: int = 100) -> list:
        """
        列出任务
        
        Args:
            task_type: 任务类型
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        try:
            r = await self._get_redis()
            pattern = f"{self.KEY_PREFIX}{task_type}:*"
            keys = []
            async for key in r.scan_iter(match=pattern, count=limit):
                keys.append(key)
                if len(keys) >= limit:
                    break
            
            if not keys:
                return []
            
            values = await r.mget(keys)
            tasks = []
            for data in values:
                if data:
                    tasks.append(json.loads(data))
            return tasks
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []
    
    async def publish_progress(self, task_type: str, task_id: str, progress_data: Dict[str, Any]):
        """
        发布进度更新（用于WebSocket推送）
        
        Args:
            task_type: 任务类型
            task_id: 任务ID
            progress_data: 进度数据
        """
        try:
            r = await self._get_redis()
            channel = f"tactiq:progress:{task_type}:{task_id}"
            await r.publish(channel, json.dumps(progress_data, default=self._json_serializer))
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")
    
    def _json_serializer(self, obj):
        """JSON序列化辅助函数"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# 全局任务存储实例
task_storage = TaskStorage()
