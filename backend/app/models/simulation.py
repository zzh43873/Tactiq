"""
推演模型
存储推演记录和结果
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, String, JSON, ForeignKey, DateTime, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.models.base import Base


class SimulationStatus(str, enum.Enum):
    """推演状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# 多对多关联表
simulation_entities = Table(
    'simulation_entities',
    Base.metadata,
    Column('simulation_id', UUID(as_uuid=True), ForeignKey('simulation.id'), primary_key=True),
    Column('entity_id', UUID(as_uuid=True), ForeignKey('entity.id'), primary_key=True)
)


class Simulation(Base):
    """
    推演记录
    
    存储推演任务和结果
    """
    
    # 关联事件
    event_id = Column(UUID(as_uuid=True), ForeignKey("event.id"), nullable=False, comment="关联事件ID")
    
    # 推演配置
    config = Column(JSON, default=dict, comment="推演配置")
    # 示例：
    # {
    #     "scenarios": ["cooperative", "confrontational", "mixed"],
    #     "time_horizons": ["short", "medium", "long"],
    #     "dimensions": ["economic", "military", "diplomatic", "public_opinion"],
    #     "max_rounds": 5
    # }
    
    # 推演状态
    status = Column(SQLEnum(SimulationStatus), default=SimulationStatus.PENDING, comment="推演状态")
    
    # 结果数据
    results = Column(JSON, default=dict, comment="推演结果")
    # 存储完整的推演结果，包括：
    # - rounds: 各轮推演结果
    # - paths: 推演路径
    # - red_team_challenges: 红队挑战
    # - synthesis: 综合评估
    
    # 错误信息
    error_message = Column(String(1000), nullable=True, comment="错误信息")
    
    # 时间戳
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    
    # 关联关系
    event = relationship("Event", back_populates="simulations")
    entities = relationship("Entity", secondary=simulation_entities, back_populates="simulations")
    
    def __repr__(self) -> str:
        return f"<Simulation(id={self.id}, status={self.status}, event_id={self.event_id})>"
    
    def get_duration_seconds(self) -> Optional[float]:
        """获取推演耗时（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
