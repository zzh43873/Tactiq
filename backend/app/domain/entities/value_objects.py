"""
值对象 (Value Objects)
不可变的数据结构，用于描述领域概念
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class DecisionDimension(str, Enum):
    """决策维度"""
    MILITARY = "military"
    DIPLOMATIC = "diplomatic"
    ECONOMIC = "economic"
    ENERGY = "energy"
    PUBLIC_OPINION = "public_opinion"


class RelationshipType(str, Enum):
    """关系类型"""
    ALLIANCE = "alliance"
    COOPERATION = "cooperation"
    TENSION = "tension"
    CONFLICT = "conflict"
    PROXY = "proxy"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class Decision:
    """
    决策值对象
    
    不可变，代表实体在某一时刻的决策
    """
    military: str = ""
    diplomatic: str = ""
    economic: str = ""
    energy: str = ""
    public_opinion: str = ""
    rationale: str = ""
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "military": self.military,
            "diplomatic": self.diplomatic,
            "economic": self.economic,
            "energy": self.energy,
            "public_opinion": self.public_opinion,
            "rationale": self.rationale,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        return cls(
            military=data.get("military", ""),
            diplomatic=data.get("diplomatic", ""),
            economic=data.get("economic", ""),
            energy=data.get("energy", ""),
            public_opinion=data.get("public_opinion", ""),
            rationale=data.get("rationale", ""),
            confidence=data.get("confidence", 0.5),
        )


@dataclass(frozen=True)
class Reaction:
    """
    反应值对象
    
    代表实体对某一事件/局势的反应
    """
    entity_name: str
    decision: Decision
    round_number: int
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "decision": self.decision.to_dict(),
            "round_number": self.round_number,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class Relationship:
    """
    关系值对象
    
    代表两个实体之间的关系
    """
    entity_a: str
    entity_b: str
    relationship_type: RelationshipType
    dimension: str = "political"  # political/security/economic/social/ideological/geostrategic
    tension_level: float = 0.5  # 0-1
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "relationship_type": self.relationship_type.value,
            "dimension": self.dimension,
            "tension_level": self.tension_level,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        return cls(
            entity_a=data["entity_a"],
            entity_b=data["entity_b"],
            relationship_type=RelationshipType(data.get("relationship_type", "neutral")),
            dimension=data.get("dimension", "political"),
            tension_level=data.get("tension_level", 0.5),
            description=data.get("description", ""),
        )


@dataclass(frozen=True)
class Source:
    """数据来源值对象"""
    name: str
    url: str
    title: str
    published_at: Optional[str] = None
    relevance_score: float = 0.0
    sentiment: str = "neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "title": self.title,
            "published_at": self.published_at,
            "relevance_score": self.relevance_score,
            "sentiment": self.sentiment,
        }
