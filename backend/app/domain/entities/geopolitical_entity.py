"""
地缘政治实体 - 领域实体
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class EntityType(str, Enum):
    """实体类型"""
    SOVEREIGN_STATE = "sovereign_state"
    NON_STATE_ACTOR = "non_state_actor"
    INTERNATIONAL_ORG = "international_org"
    MULTINATIONAL_CORP = "multinational_corp"
    REGIONAL_POWER = "regional_power"
    REGION = "region"
    ORGANIZATION = "organization"


class EntityRole(str, Enum):
    """实体在事件中的角色"""
    INITIATOR = "initiator"
    TARGET = "target"
    ALLY = "ally"
    ADVERSARY = "adversary"
    STAKEHOLDER = "stakeholder"
    PROXY = "proxy"
    MEDIATOR = "mediator"
    NEUTRAL = "neutral"


@dataclass
class EntityCapabilities:
    """实体能力评估"""
    economic_power: float = 0.0
    military_power: float = 0.0
    diplomatic_influence: float = 0.0
    domestic_stability: float = 0.0
    strategic_patience: float = 0.0
    risk_tolerance: float = 0.0


@dataclass
class GeopoliticalEntity:
    """
    地缘政治实体
    
    这是领域的核心概念，代表参与地缘政治推演的各种行为体
    """
    name: str
    name_en: Optional[str] = None
    entity_type: EntityType = EntityType.SOVEREIGN_STATE
    role: EntityRole = EntityRole.STAKEHOLDER
    relevance_score: float = 0.5
    
    # 核心利益
    core_interests: List[str] = field(default_factory=list)
    
    # 能力评估
    capabilities: EntityCapabilities = field(default_factory=EntityCapabilities)
    
    # 当前行动
    current_actions: List[str] = field(default_factory=list)
    
    # 公开立场
    stated_position: str = ""
    
    # 背景资料
    background_profile: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_role(self, new_role: EntityRole) -> None:
        """更新实体角色"""
        self.role = new_role
    
    def add_core_interest(self, interest: str) -> None:
        """添加核心利益"""
        if interest not in self.core_interests:
            self.core_interests.append(interest)
    
    def update_capabilities(self, **kwargs) -> None:
        """更新能力评估"""
        for key, value in kwargs.items():
            if hasattr(self.capabilities, key):
                setattr(self.capabilities, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "name_en": self.name_en,
            "entity_type": self.entity_type.value,
            "role": self.role.value,
            "relevance_score": self.relevance_score,
            "core_interests": self.core_interests,
            "capabilities": {
                "economic_power": self.capabilities.economic_power,
                "military_power": self.capabilities.military_power,
                "diplomatic_influence": self.capabilities.diplomatic_influence,
                "domestic_stability": self.capabilities.domestic_stability,
                "strategic_patience": self.capabilities.strategic_patience,
                "risk_tolerance": self.capabilities.risk_tolerance,
            },
            "current_actions": self.current_actions,
            "stated_position": self.stated_position,
            "background_profile": self.background_profile,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeopoliticalEntity":
        """从字典创建"""
        capabilities_data = data.get("capabilities", {})
        capabilities = EntityCapabilities(
            economic_power=capabilities_data.get("economic_power", 0.0),
            military_power=capabilities_data.get("military_power", 0.0),
            diplomatic_influence=capabilities_data.get("diplomatic_influence", 0.0),
            domestic_stability=capabilities_data.get("domestic_stability", 0.0),
            strategic_patience=capabilities_data.get("strategic_patience", 0.0),
            risk_tolerance=capabilities_data.get("risk_tolerance", 0.0),
        )
        
        return cls(
            name=data["name"],
            name_en=data.get("name_en"),
            entity_type=EntityType(data.get("entity_type", "sovereign_state")),
            role=EntityRole(data.get("role", "stakeholder")),
            relevance_score=data.get("relevance_score", 0.5),
            core_interests=data.get("core_interests", []),
            capabilities=capabilities,
            current_actions=data.get("current_actions", []),
            stated_position=data.get("stated_position", ""),
            background_profile=data.get("background_profile", ""),
            metadata=data.get("metadata", {}),
        )
