"""
情报仓储实现
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from .base import AsyncRepository
from app.models.intelligence_cache import IntelligenceCache


class IntelligenceRepository(AsyncRepository[Dict[str, Any]]):
    """
    情报仓储接口
    
    定义情报相关的数据访问操作
    """
    
    async def get_by_event_description(self, event_description: str) -> Optional[Dict[str, Any]]:
        """根据事件描述获取情报"""
        pass
    
    async def get_fresh_cache(self, event_description: str, max_age_hours: int = 168) -> Optional[Dict[str, Any]]:
        """获取新鲜缓存"""
        pass
    
    async def list_recent(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """列出最近的情报记录"""
        pass


class SQLAlchemyIntelligenceRepository(IntelligenceRepository):
    """
    SQLAlchemy 情报仓储实现
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_id(self, id: UUID) -> Optional[Dict[str, Any]]:
        """根据ID获取情报"""
        try:
            result = await self._session.execute(
                select(IntelligenceCache).where(IntelligenceCache.id == id)
            )
            orm_obj = result.scalar_one_or_none()
            return self._to_dict(orm_obj) if orm_obj else None
        except Exception as e:
            logger.error(f"Error getting intelligence by id: {e}")
            return None
    
    async def list(self, **filters) -> List[Dict[str, Any]]:
        """列出情报记录"""
        try:
            query = select(IntelligenceCache)
            
            if "limit" in filters:
                query = query.limit(filters["limit"])
            if "offset" in filters:
                query = query.offset(filters["offset"])
            
            query = query.order_by(desc(IntelligenceCache.created_at))
            
            result = await self._session.execute(query)
            orm_objs = result.scalars().all()
            return [self._to_dict(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(f"Error listing intelligence: {e}")
            return []
    
    async def add(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """添加情报记录"""
        try:
            orm_obj = IntelligenceCache(
                event_description=entity["event_description"],
                pre_identified_entities=entity.get("pre_identified_entities", []),
                pre_identified_relationships=entity.get("pre_identified_relationships", []),
                expanded_queries=entity.get("expanded_queries", []),
                collected_articles=entity.get("collected_articles", []),
                identified_entities=entity.get("identified_entities", []),
                relationship_dynamics=entity.get("relationship_dynamics", {}),
                simulation_result=entity.get("simulation_result"),
                last_article_date=entity.get("last_article_date"),
            )
            self._session.add(orm_obj)
            await self._session.flush()
            return self._to_dict(orm_obj)
        except Exception as e:
            logger.error(f"Error adding intelligence: {e}")
            raise
    
    async def update(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """更新情报记录"""
        try:
            result = await self._session.execute(
                select(IntelligenceCache).where(IntelligenceCache.id == entity["id"])
            )
            orm_obj = result.scalar_one_or_none()
            if not orm_obj:
                raise ValueError(f"Intelligence not found: {entity['id']}")
            
            # 更新字段
            for key in [
                "pre_identified_entities",
                "pre_identified_relationships", 
                "expanded_queries",
                "collected_articles",
                "identified_entities",
                "relationship_dynamics",
                "simulation_result",
                "last_article_date",
            ]:
                if key in entity:
                    setattr(orm_obj, key, entity[key])
            
            await self._session.flush()
            return self._to_dict(orm_obj)
        except Exception as e:
            logger.error(f"Error updating intelligence: {e}")
            raise
    
    async def delete(self, id: UUID) -> bool:
        """删除情报记录"""
        try:
            result = await self._session.execute(
                select(IntelligenceCache).where(IntelligenceCache.id == id)
            )
            orm_obj = result.scalar_one_or_none()
            if orm_obj:
                await self._session.delete(orm_obj)
                await self._session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting intelligence: {e}")
            return False
    
    async def exists(self, id: UUID) -> bool:
        """检查情报记录是否存在"""
        try:
            result = await self._session.execute(
                select(IntelligenceCache).where(IntelligenceCache.id == id)
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking intelligence existence: {e}")
            return False
    
    async def count(self, **filters) -> int:
        """统计情报记录数量"""
        try:
            query = select(IntelligenceCache)
            result = await self._session.execute(query)
            return len(result.scalars().all())
        except Exception as e:
            logger.error(f"Error counting intelligence: {e}")
            return 0
    
    async def get_by_event_description(self, event_description: str) -> Optional[Dict[str, Any]]:
        """根据事件描述获取情报"""
        try:
            result = await self._session.execute(
                select(IntelligenceCache)
                .where(IntelligenceCache.event_description == event_description)
                .order_by(desc(IntelligenceCache.created_at))
            )
            orm_obj = result.scalars().first()
            return self._to_dict(orm_obj) if orm_obj else None
        except Exception as e:
            logger.error(f"Error getting intelligence by description: {e}")
            return None
    
    async def get_fresh_cache(self, event_description: str, max_age_hours: int = 168) -> Optional[Dict[str, Any]]:
        """获取新鲜缓存"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            result = await self._session.execute(
                select(IntelligenceCache)
                .where(
                    and_(
                        IntelligenceCache.event_description == event_description,
                        IntelligenceCache.created_at >= cutoff_time
                    )
                )
                .order_by(desc(IntelligenceCache.created_at))
            )
            orm_obj = result.scalars().first()
            return self._to_dict(orm_obj) if orm_obj else None
        except Exception as e:
            logger.error(f"Error getting fresh cache: {e}")
            return None
    
    async def list_recent(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """列出最近的情报记录"""
        return await self.list(limit=limit, offset=offset)
    
    def _to_dict(self, orm_obj: IntelligenceCache) -> Dict[str, Any]:
        """将ORM对象转换为字典"""
        if not orm_obj:
            return None
        
        return {
            "id": str(orm_obj.id),
            "event_description": orm_obj.event_description,
            "pre_identified_entities": orm_obj.pre_identified_entities,
            "pre_identified_relationships": orm_obj.pre_identified_relationships,
            "expanded_queries": orm_obj.expanded_queries,
            "collected_articles": orm_obj.collected_articles,
            "identified_entities": orm_obj.identified_entities,
            "relationship_dynamics": orm_obj.relationship_dynamics,
            "simulation_result": orm_obj.simulation_result,
            "last_article_date": orm_obj.last_article_date.isoformat() if orm_obj.last_article_date else None,
            "created_at": orm_obj.created_at.isoformat() if orm_obj.created_at else None,
            "updated_at": orm_obj.updated_at.isoformat() if orm_obj.updated_at else None,
        }
