"""
事件模型
存储地缘政治事件
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, String, Float, JSON, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Event(Base):
    """
    地缘政治事件
    
    存储国际事件、冲突、外交活动等
    """
    
    # 基本信息
    title = Column(String(500), nullable=False, comment="事件标题")
    description = Column(Text, nullable=True, comment="事件描述")
    
    # 时间信息
    event_date = Column(DateTime(timezone=True), nullable=True, comment="事件发生时间")
    reported_date = Column(DateTime(timezone=True), nullable=True, comment="报道时间")
    
    # 地理位置
    location = Column(JSON, default=dict, comment="地理位置信息")
    # 示例：
    # {
    #     "country": "伊朗",
    #     "region": "中东",
    #     "city": "德黑兰",
    #     "coordinates": {"lat": 35.6892, "lng": 51.3890}
    # }
    
    # 涉及实体
    primary_actor_id = Column(UUID(as_uuid=True), ForeignKey("entity.id"), nullable=True, comment="主要行为体")
    target_id = Column(UUID(as_uuid=True), ForeignKey("entity.id"), nullable=True, comment="目标")
    involved_entities = Column(JSON, default=list, comment="涉及实体列表")
    
    # 事件分类
    event_type = Column(String(50), nullable=True, comment="事件类型")
    # 示例：conflict, diplomatic, economic, military, etc.
    
    intensity = Column(Float, nullable=True, comment="事件强度 0-1")
    
    # 维度影响
    dimension_impacts = Column(JSON, default=dict, comment="维度影响")
    # 示例：
    # {
    #     "economic": 0.7,
    #     "military": 0.8,
    #     "diplomatic": 0.6,
    #     "public_opinion": 0.5
    # }
    
    # 数据来源
    sources = Column(JSON, default=list, comment="数据来源")
    # 示例：
    # [
    #     {"name": "Reuters", "url": "...", "published_at": "...", "reliability": 0.9},
    #     {"name": "BBC", "url": "...", "published_at": "...", "reliability": 0.85}
    # ]
    
    # 原始情报数据
    raw_intelligence = Column(JSON, default=dict, comment="原始情报数据")
    
    # 关联关系
    primary_actor = relationship("Entity", foreign_keys=[primary_actor_id], back_populates="events_as_primary")
    target = relationship("Entity", foreign_keys=[target_id], back_populates="events_as_target")
    simulations = relationship("Simulation", back_populates="event")
    
    def __repr__(self) -> str:
        return f"<Event(title={self.title[:50]}..., type={self.event_type})>"
