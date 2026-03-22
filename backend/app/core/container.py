"""
依赖注入容器

管理服务实例的生命周期和依赖关系
"""
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.infrastructure.external.llm import LLMProvider, LLMFactory
from app.infrastructure.repositories import (
    SimulationRepository,
    IntelligenceRepository,
    SQLAlchemySimulationRepository,
    SQLAlchemyIntelligenceRepository,
)
from app.application import (
    SimulationApplicationService,
    IntelligenceApplicationService,
)


class ServiceContainer:
    """
    服务容器
    
    使用依赖注入模式管理服务实例
    """
    
    def __init__(self):
        self._llm_provider: Optional[LLMProvider] = None
    
    def get_llm_provider(self) -> LLMProvider:
        """获取LLM Provider（单例）"""
        if self._llm_provider is None:
            self._llm_provider = LLMFactory.create()
        return self._llm_provider
    
    @asynccontextmanager
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        session = AsyncSessionLocal()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def get_simulation_repository(self) -> AsyncGenerator[SimulationRepository, None]:
        """获取推演仓储"""
        async with self.get_db_session() as session:
            yield SQLAlchemySimulationRepository(session)
    
    async def get_intelligence_repository(self) -> AsyncGenerator[IntelligenceRepository, None]:
        """获取情报仓储"""
        async with self.get_db_session() as session:
            yield SQLAlchemyIntelligenceRepository(session)
    
    async def get_simulation_service(self) -> AsyncGenerator[SimulationApplicationService, None]:
        """获取推演应用服务（带 LangGraph 引擎）"""
        async with self.get_db_session() as session:
            repository = SQLAlchemySimulationRepository(session)
            llm = self.get_llm_provider()
            yield SimulationApplicationService(repository, llm)
    
    async def get_intelligence_service(self) -> AsyncGenerator[IntelligenceApplicationService, None]:
        """获取情报应用服务"""
        async with self.get_db_session() as session:
            repository = SQLAlchemyIntelligenceRepository(session)
            llm = self.get_llm_provider()
            yield IntelligenceApplicationService(repository, llm)


# 全局服务容器实例
container = ServiceContainer()
