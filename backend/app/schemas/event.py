"""
事件相关Schema
"""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class DimensionImpact(BaseModel):
    """维度影响"""
    economic: float = Field(default=0.0, ge=-1.0, le=1.0)
    military: float = Field(default=0.0, ge=-1.0, le=1.0)
    diplomatic: float = Field(default=0.0, ge=-1.0, le=1.0)
    public_opinion: float = Field(default=0.0, ge=-1.0, le=1.0)


class EventSource(BaseModel):
    """事件来源"""
    name: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)


class EventBase(BaseModel):
    """事件基础Schema"""
    title: str = Field(..., description="事件标题")
    description: Optional[str] = Field(default=None, description="事件描述")
    event_date: Optional[datetime] = Field(default=None, description="事件发生时间")


class EventCreate(EventBase):
    """创建事件请求"""
    location: Optional[Dict] = Field(default=None, description="地理位置")
    primary_actor_id: Optional[UUID] = Field(default=None, description="主要行为体")
    target_id: Optional[UUID] = Field(default=None, description="目标")
    involved_entities: List[UUID] = Field(default=[], description="涉及实体")
    event_type: Optional[str] = Field(default=None, description="事件类型")
    intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="强度")
    dimension_impacts: Optional[DimensionImpact] = Field(default=None)
    sources: Optional[List[EventSource]] = Field(default=None)


class Event(EventBase):
    """事件响应Schema"""
    id: UUID
    location: Optional[Dict]
    primary_actor_id: Optional[UUID]
    target_id: Optional[UUID]
    involved_entities: List[UUID]
    event_type: Optional[str]
    intensity: Optional[float]
    dimension_impacts: DimensionImpact
    sources: List[EventSource]
    reported_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class EntityStance(BaseModel):
    """实体立场"""
    entity_id: UUID
    entity_name: str
    stance: float = Field(..., ge=-1.0, le=1.0, description="立场倾向 -1反对到1支持")
    interest_relevance: str = Field(..., description="利益相关度高/中/低")
    action_willingness: str = Field(..., description="行动意愿高/中/低")
    key_interests: List[str] = Field(default=[], description="相关核心利益")


class EventAnalysis(BaseModel):
    """事件分析结果"""
    event_id: UUID
    entities: List[EntityStance]
    key_factors: List[str] = Field(default=[], description="关键因素")
    potential_escalation: float = Field(..., ge=0.0, le=1.0, description="升级可能性")
    summary: str = Field(..., description="分析摘要")


class IntelligenceRequest(BaseModel):
    """情报收集请求"""
    event_description: str = Field(..., description="事件描述")
    time_range: str = Field(default="past_30_days", description="时间范围")
    sources: List[str] = Field(default=["gdelt", "newsapi"], description="数据源")


class IntelligenceResponse(BaseModel):
    """情报收集响应"""
    task_id: str
    status: str
    estimated_time: int
    message: str
