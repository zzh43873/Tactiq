"""
仓储模式实现 (Repository Pattern)

提供领域对象的持久化抽象，隔离领域层与数据访问层
"""
from .base import Repository, AsyncRepository
from .simulation_repository import SimulationRepository, SQLAlchemySimulationRepository
from .intelligence_repository import IntelligenceRepository, SQLAlchemyIntelligenceRepository

__all__ = [
    "Repository",
    "AsyncRepository",
    "SimulationRepository",
    "SQLAlchemySimulationRepository",
    "IntelligenceRepository",
    "SQLAlchemyIntelligenceRepository",
]
