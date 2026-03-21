"""
情报缓存服务
管理情报收集结果的缓存、查询和增量更新
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.intelligence_cache import IntelligenceCache


class IntelligenceCacheService:
    """
    情报缓存服务
    
    提供以下功能：
    1. 查询缓存（基于事件描述的哈希）
    2. 保存缓存结果
    3. 增量更新检测
    4. 历史记录查询
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _generate_query_hash(self, event_description: str) -> str:
        """
        生成查询哈希
        
        使用SHA256对规范化后的事件描述进行哈希
        """
        # 规范化：去除首尾空格，统一小写
        normalized = event_description.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    async def get_cache(
        self, 
        event_description: str,
        max_age_hours: int = 24
    ) -> Optional[IntelligenceCache]:
        """
        获取缓存
        
        Args:
            event_description: 事件描述
            max_age_hours: 最大缓存时间（小时）
            
        Returns:
            缓存记录，如果不存在或已过期返回None
        """
        query_hash = self._generate_query_hash(event_description)
        
        result = await self.db.execute(
            select(IntelligenceCache).where(
                IntelligenceCache.query_hash == query_hash
            )
        )
        cache = result.scalar_one_or_none()
        
        if not cache:
            return None
        
        # 检查是否过期
        if not cache.is_fresh(max_age_hours):
            logger.info(f"Cache expired for query: {event_description[:50]}...")
            return None
        
        # 更新命中次数和访问时间
        cache.hit_count += 1
        # Safely set last_accessed_at if the attribute exists
        if hasattr(cache, 'last_accessed_at'):
            cache.last_accessed_at = datetime.now()
        await self.db.commit()
        
        logger.info(f"Cache hit for query: {event_description[:50]}... (hits: {cache.hit_count})")
        return cache
    
    async def get_cache_status(
        self, 
        event_description: str
    ) -> Dict[str, Any]:
        """
        获取缓存状态（用于判断是否可以使用缓存或需要增量更新）
        
        Returns:
            {
                "exists": bool,
                "is_fresh": bool,
                "needs_incremental": bool,
                "cache": IntelligenceCache | None
            }
        """
        query_hash = self._generate_query_hash(event_description)
        
        result = await self.db.execute(
            select(IntelligenceCache).where(
                IntelligenceCache.query_hash == query_hash
            )
        )
        cache = result.scalar_one_or_none()
        
        if not cache:
            return {
                "exists": False,
                "is_fresh": False,
                "needs_incremental": False,
                "cache": None
            }
        
        return {
            "exists": True,
            "is_fresh": cache.is_fresh(),
            "needs_incremental": cache.needs_incremental_update(),
            "cache": cache
        }
    
    async def save_cache(
        self,
        event_description: str,
        pre_identified_entities: Optional[List[Dict]] = None,
        pre_identified_relationships: Optional[List[Dict]] = None,
        expanded_queries: Optional[List[Dict]] = None,
        collected_articles: Optional[List[Dict]] = None,
        identified_entities: Optional[List[Dict]] = None,
        relationship_dynamics: Optional[Dict] = None,
        last_article_date: Optional[datetime] = None,
        simulation_result: Optional[Dict] = None
    ) -> IntelligenceCache:
        """
        保存缓存
        
        Args:
            event_description: 事件描述
            pre_identified_entities: 预识别实体（为None时保留原值）
            pre_identified_relationships: 预识别关系（为None时保留原值）
            expanded_queries: 扩展查询（为None时保留原值）
            collected_articles: 收集的文章（为None时保留原值）
            identified_entities: 最终识别的实体（为None时保留原值）
            relationship_dynamics: 关系动态（为None时保留原值）
            last_article_date: 最后文章日期
            simulation_result: 推演结果（为None时保留原值）
            
        Returns:
            保存的缓存记录
        """
        query_hash = self._generate_query_hash(event_description)
        
        # 检查是否已存在
        result = await self.db.execute(
            select(IntelligenceCache).where(
                IntelligenceCache.query_hash == query_hash
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 更新现有缓存 - 只更新传入的非None值
            if pre_identified_entities is not None:
                existing.pre_identified_entities = pre_identified_entities
            if pre_identified_relationships is not None:
                existing.pre_identified_relationships = pre_identified_relationships
            if expanded_queries is not None:
                existing.expanded_queries = expanded_queries
            if collected_articles is not None:
                existing.collected_articles = collected_articles
            if identified_entities is not None:
                existing.identified_entities = identified_entities
            if relationship_dynamics is not None:
                existing.relationship_dynamics = relationship_dynamics
            if last_article_date is not None:
                existing.last_article_date = last_article_date
            if simulation_result is not None:
                existing.simulation_result = simulation_result
            existing.updated_at = datetime.now()
            # Safely set last_accessed_at if the attribute exists
            if hasattr(existing, 'last_accessed_at'):
                existing.last_accessed_at = datetime.now()
            
            await self.db.commit()
            logger.info(f"Updated cache for query: {event_description[:50]}...")
            return existing
        else:
            # 创建新缓存
            cache = IntelligenceCache(
                query_hash=query_hash,
                event_description=event_description,
                pre_identified_entities=pre_identified_entities,
                pre_identified_relationships=pre_identified_relationships,
                expanded_queries=expanded_queries,
                collected_articles=collected_articles,
                identified_entities=identified_entities,
                relationship_dynamics=relationship_dynamics,
                simulation_result=simulation_result,
                last_article_date=last_article_date,
                hit_count=1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_accessed_at=datetime.now()
            )
            
            self.db.add(cache)
            await self.db.commit()
            await self.db.refresh(cache)
            
            logger.info(f"Created new cache for query: {event_description[:50]}...")
            return cache
    
    async def get_history(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[IntelligenceCache]:
        """
        获取历史记录
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            缓存记录列表（按更新时间倒序）
        """
        result = await self.db.execute(
            select(IntelligenceCache)
            .order_by(desc(IntelligenceCache.updated_at))
            .limit(limit)
            .offset(offset)
        )
        
        return list(result.scalars().all())
    
    async def get_incremental_date_range(
        self,
        event_description: str
    ) -> Optional[Dict[str, datetime]]:
        """
        获取增量更新的日期范围
        
        如果缓存存在且需要增量更新，返回需要获取的日期范围
        
        Returns:
            {
                "start_date": datetime,  # 从上次更新日期的下一天开始
                "end_date": datetime     # 到今天
            }
            或 None（如果不需要增量更新）
        """
        query_hash = self._generate_query_hash(event_description)
        
        result = await self.db.execute(
            select(IntelligenceCache).where(
                IntelligenceCache.query_hash == query_hash
            )
        )
        cache = result.scalar_one_or_none()
        
        if not cache or not cache.needs_incremental_update():
            return None
        
        # 从上次更新日期的下一天开始
        start_date = cache.updated_at + timedelta(days=1)
        end_date = datetime.now()
        
        # 如果开始日期已经超过今天，不需要更新
        if start_date.date() > end_date.date():
            return None
        
        return {
            "start_date": start_date,
            "end_date": end_date
        }
    
    async def delete_old_caches(self, max_age_days: int = 30) -> int:
        """
        删除过期的缓存
        
        Args:
            max_age_days: 最大保留天数
            
        Returns:
            删除的记录数
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        result = await self.db.execute(
            select(IntelligenceCache).where(
                IntelligenceCache.updated_at < cutoff_date
            )
        )
        old_caches = result.scalars().all()
        
        count = 0
        for cache in old_caches:
            await self.db.delete(cache)
            count += 1
        
        await self.db.commit()
        logger.info(f"Deleted {count} old caches (older than {max_age_days} days)")
        
        return count
