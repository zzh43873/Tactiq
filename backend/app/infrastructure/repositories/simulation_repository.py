"""
推演仓储实现
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from .base import AsyncRepository
from app.models.simulation import Simulation as SimulationORM, SimulationStatus


class SimulationRepository(AsyncRepository[Dict[str, Any]]):
    """
    推演仓储接口
    
    定义推演相关的数据访问操作
    """
    
    async def get_by_proposition(self, proposition: str) -> Optional[Dict[str, Any]]:
        """根据命题获取推演"""
        pass
    
    async def list_by_status(self, status: SimulationStatus, limit: int = 100) -> List[Dict[str, Any]]:
        """根据状态列出推演"""
        pass
    
    async def update_status(self, id: UUID, status: SimulationStatus, error_message: str = None) -> bool:
        """更新推演状态"""
        pass
    
    async def update_results(self, id: UUID, results: Dict[str, Any]) -> bool:
        """更新推演结果"""
        pass


class SQLAlchemySimulationRepository(SimulationRepository):
    """
    SQLAlchemy 推演仓储实现
    
    使用PostgreSQL存储推演数据
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_id(self, id: UUID) -> Optional[Dict[str, Any]]:
        """根据ID获取推演"""
        try:
            result = await self._session.execute(
                select(SimulationORM).where(SimulationORM.id == id)
            )
            orm_obj = result.scalar_one_or_none()
            return self._to_dict(orm_obj) if orm_obj else None
        except Exception as e:
            logger.error(f"Error getting simulation by id: {e}")
            return None
    
    async def list(self, **filters) -> List[Dict[str, Any]]:
        """列出推演，支持过滤"""
        try:
            query = select(SimulationORM)
            
            # 应用过滤条件
            if "status" in filters:
                query = query.where(SimulationORM.status == filters["status"])
            if "event_id" in filters:
                query = query.where(SimulationORM.event_id == filters["event_id"])
            
            # 排序和分页
            query = query.order_by(desc(SimulationORM.created_at))
            
            if "limit" in filters:
                query = query.limit(filters["limit"])
            if "offset" in filters:
                query = query.offset(filters["offset"])
            
            result = await self._session.execute(query)
            orm_objs = result.scalars().all()
            return [self._to_dict(obj) for obj in orm_objs]
        except Exception as e:
            logger.error(f"Error listing simulations: {e}")
            return []
    
    async def add(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """添加推演"""
        try:
            orm_obj = SimulationORM(
                id=entity.get("id"),
                event_id=entity.get("event_id"),
                config=entity.get("config", {}),
                status=SimulationStatus(entity.get("status", "pending")),
                started_at=entity.get("started_at"),
            )
            self._session.add(orm_obj)
            await self._session.flush()
            return self._to_dict(orm_obj)
        except Exception as e:
            logger.error(f"Error adding simulation: {e}")
            raise
    
    async def update(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """更新推演"""
        try:
            result = await self._session.execute(
                select(SimulationORM).where(SimulationORM.id == entity["id"])
            )
            orm_obj = result.scalar_one_or_none()
            if not orm_obj:
                raise ValueError(f"Simulation not found: {entity['id']}")
            
            # 更新字段
            if "config" in entity:
                orm_obj.config = entity["config"]
            if "status" in entity:
                orm_obj.status = SimulationStatus(entity["status"])
            if "results" in entity:
                orm_obj.results = entity["results"]
            if "error_message" in entity:
                orm_obj.error_message = entity["error_message"]
            if "completed_at" in entity:
                orm_obj.completed_at = entity["completed_at"]
            
            await self._session.flush()
            return self._to_dict(orm_obj)
        except Exception as e:
            logger.error(f"Error updating simulation: {e}")
            raise
    
    async def delete(self, id: UUID) -> bool:
        """删除推演"""
        try:
            result = await self._session.execute(
                select(SimulationORM).where(SimulationORM.id == id)
            )
            orm_obj = result.scalar_one_or_none()
            if orm_obj:
                await self._session.delete(orm_obj)
                await self._session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting simulation: {e}")
            return False
    
    async def exists(self, id: UUID) -> bool:
        """检查推演是否存在"""
        try:
            result = await self._session.execute(
                select(SimulationORM).where(SimulationORM.id == id)
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking simulation existence: {e}")
            return False
    
    async def count(self, **filters) -> int:
        """统计推演数量"""
        try:
            query = select(SimulationORM)
            if "status" in filters:
                query = query.where(SimulationORM.status == filters["status"])
            
            result = await self._session.execute(query)
            return len(result.scalars().all())
        except Exception as e:
            logger.error(f"Error counting simulations: {e}")
            return 0
    
    async def get_by_proposition(self, proposition: str) -> Optional[Dict[str, Any]]:
        """根据命题获取推演（通过event关联）"""
        # 需要通过Event表关联查询
        # 这里简化处理，实际应该join Event表
        return None
    
    async def list_by_status(self, status: SimulationStatus, limit: int = 100) -> List[Dict[str, Any]]:
        """根据状态列出推演"""
        return await self.list(status=status, limit=limit)
    
    async def update_status(self, id: UUID, status: SimulationStatus, error_message: str = None) -> bool:
        """更新推演状态"""
        try:
            result = await self._session.execute(
                select(SimulationORM).where(SimulationORM.id == id)
            )
            orm_obj = result.scalar_one_or_none()
            if not orm_obj:
                return False
            
            orm_obj.status = status
            if error_message:
                orm_obj.error_message = error_message
            
            if status == SimulationStatus.COMPLETED:
                orm_obj.completed_at = datetime.now()
            
            await self._session.flush()
            return True
        except Exception as e:
            logger.error(f"Error updating simulation status: {e}")
            return False
    
    async def update_results(self, id: UUID, results: Dict[str, Any]) -> bool:
        """更新推演结果"""
        try:
            result = await self._session.execute(
                select(SimulationORM).where(SimulationORM.id == id)
            )
            orm_obj = result.scalar_one_or_none()
            if not orm_obj:
                return False
            
            orm_obj.results = results
            await self._session.flush()
            return True
        except Exception as e:
            logger.error(f"Error updating simulation results: {e}")
            return False
    
    def _to_dict(self, orm_obj: SimulationORM) -> Dict[str, Any]:
        """将ORM对象转换为字典"""
        if not orm_obj:
            return None
        
        return {
            "id": str(orm_obj.id),
            "event_id": str(orm_obj.event_id) if orm_obj.event_id else None,
            "config": orm_obj.config,
            "status": orm_obj.status.value,
            "results": orm_obj.results,
            "error_message": orm_obj.error_message,
            "started_at": orm_obj.started_at.isoformat() if orm_obj.started_at else None,
            "completed_at": orm_obj.completed_at.isoformat() if orm_obj.completed_at else None,
            "created_at": orm_obj.created_at.isoformat() if orm_obj.created_at else None,
        }
