"""
实体模型
存储地缘政治实体（国家、组织、武装团体）
"""

from typing import Optional, List
from sqlalchemy import Column, String, Float, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class EntityType(str, enum.Enum):
    """实体类型"""
    SOVEREIGN_STATE = "sovereign_state"      # 主权国家
    STATE_ALLIANCE = "state_alliance"        # 国家联盟
    INTERNATIONAL_ORG = "international_org"  # 国际组织
    NON_STATE_ARMED = "non_state_armed"      # 非国家武装
    MULTINATIONAL_CORP = "multinational_corp"  # 跨国企业
    REGIONAL_POWER = "regional_power"        # 地区势力


class Entity(Base):
    """
    地缘政治实体
    
    存储国家、组织、武装团体等实体的基础信息
    """
    
    # 基本信息
    name = Column(String(100), nullable=False, index=True, comment="实体名称（中文）")
    name_en = Column(String(100), nullable=True, index=True, comment="实体名称（英文）")
    entity_type = Column(SQLEnum(EntityType), nullable=False, comment="实体类型")
    description = Column(String(500), nullable=True, comment="实体描述")
    
    # 属性配置（JSON格式，灵活扩展）
    attributes = Column(JSON, default=dict, comment="属性配置")
    # 示例：
    # {
    #     "economic_power": 0.95,      # 经济实力 0-1
    #     "military_power": 0.95,      # 军事实力 0-1
    #     "diplomatic_influence": 0.9,  # 外交影响力 0-1
    #     "domestic_stability": 0.7,   # 国内稳定性 0-1
    #     "strategic_patience": 0.6,   # 战略耐心 0-1
    #     "risk_tolerance": 0.5        # 风险承受度 0-1
    # }
    
    # 核心利益
    core_interests = Column(JSON, default=list, comment="核心利益列表")
    
    # 关系网络
    relationships = Column(JSON, default=dict, comment="关系网络")
    # 示例：
    # {
    #     "allies": ["以色列", "沙特"],
    #     "adversaries": ["伊朗", "俄罗斯"],
    #     "complex": ["土耳其"]
    # }
    
    # Agent配置
    agent_config = Column(JSON, default=dict, comment="Agent配置")
    # 示例：
    # {
    #     "decision_style": "rational",
    #     "communication_style": "formal",
    #     "priority_dimensions": ["economic", "security"]
    # }
    
    # 关联关系
    events_as_primary = relationship("Event", foreign_keys="Event.primary_actor_id", back_populates="primary_actor")
    events_as_target = relationship("Event", foreign_keys="Event.target_id", back_populates="target")
    simulations = relationship("Simulation", secondary="simulation_entities", back_populates="entities")
    
    def __repr__(self) -> str:
        return f"<Entity(name={self.name}, type={self.entity_type})>"
    
    def get_default_attributes(self) -> dict:
        """获取默认属性模板"""
        return {
            "economic_power": 0.5,
            "military_power": 0.5,
            "diplomatic_influence": 0.5,
            "domestic_stability": 0.5,
            "strategic_patience": 0.5,
            "risk_tolerance": 0.5
        }
