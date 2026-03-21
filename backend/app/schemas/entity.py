"""
实体相关Schema
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


class EntityType(str, Enum):
    """实体类型枚举"""
    SOVEREIGN_STATE = "sovereign_state"      # 主权国家
    STATE_ALLIANCE = "state_alliance"        # 国家联盟
    INTERNATIONAL_ORG = "international_org"  # 国际组织
    NON_STATE_ARMED = "non_state_armed"      # 非国家武装
    MULTINATIONAL_CORP = "multinational_corp" # 跨国企业
    REGIONAL_POWER = "regional_power"        # 地区势力


class EntityAttributes(BaseModel):
    """实体属性"""
    economic_power: float = Field(default=0.0, ge=0.0, le=1.0, description="经济实力")
    military_power: float = Field(default=0.0, ge=0.0, le=1.0, description="军事实力")
    diplomatic_influence: float = Field(default=0.0, ge=0.0, le=1.0, description="外交影响力")
    domestic_stability: float = Field(default=0.0, ge=0.0, le=1.0, description="国内稳定性")
    strategic_patience: float = Field(default=0.0, ge=0.0, le=1.0, description="战略耐心")
    risk_tolerance: float = Field(default=0.0, ge=0.0, le=1.0, description="风险承受度")


class EntityRelationships(BaseModel):
    """实体关系"""
    allies: List[str] = Field(default=[], description="盟友")
    adversaries: List[str] = Field(default=[], description="对手")
    complex: List[str] = Field(default=[], description="复杂关系")


class EntityAgentConfig(BaseModel):
    """实体Agent配置"""
    decision_style: str = Field(default="rational", description="决策风格")
    communication_style: str = Field(default="formal", description="沟通风格")
    priority_dimensions: List[str] = Field(default=["economic", "security"], description="优先维度")


class EntityBase(BaseModel):
    """实体基础Schema"""
    name: str = Field(..., description="实体名称")
    name_en: Optional[str] = Field(default=None, description="英文名称")
    entity_type: EntityType = Field(..., description="实体类型")
    description: Optional[str] = Field(default=None, description="描述")


class EntityCreate(EntityBase):
    """创建实体请求"""
    attributes: EntityAttributes = Field(default_factory=EntityAttributes)
    core_interests: List[str] = Field(default=[], description="核心利益")
    relationships: EntityRelationships = Field(default_factory=EntityRelationships)
    agent_config: EntityAgentConfig = Field(default_factory=EntityAgentConfig)


class EntityUpdate(BaseModel):
    """更新实体请求"""
    name: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    attributes: Optional[EntityAttributes] = None
    core_interests: Optional[List[str]] = None
    relationships: Optional[EntityRelationships] = None
    agent_config: Optional[EntityAgentConfig] = None


class Entity(EntityBase):
    """实体响应Schema"""
    id: UUID
    attributes: EntityAttributes
    core_interests: List[str]
    relationships: EntityRelationships
    agent_config: EntityAgentConfig
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EntityList(BaseModel):
    """实体列表响应"""
    items: List[Entity]
    total: int
    page: int
    page_size: int
