"""
Pydantic Schema定义
用于API请求/响应的数据验证和序列化
"""

from .entity import Entity, EntityCreate, EntityUpdate, EntityType, EntityList
from .event import (
    Event, EventCreate, EventAnalysis,
    IntelligenceRequest, IntelligenceResponse,
    EntityStance, DimensionImpact
)
from .simulation import (
    SimulationRequest,
    SimulationResponse,
    SimulationStatus,
    SimulationConfig,
    SimulationPath,
    SimulationList,
    TimelineNode,
    RoundResult,
    AgentAction,
    Interaction,
    Action,
    RedTeamChallenge,
    Synthesis
)

__all__ = [
    "Entity",
    "EntityCreate",
    "EntityUpdate",
    "EntityType",
    "EntityList",
    "Event",
    "EventCreate",
    "EventAnalysis",
    "IntelligenceRequest",
    "IntelligenceResponse",
    "EntityStance",
    "DimensionImpact",
    "SimulationRequest",
    "SimulationResponse",
    "SimulationStatus",
    "SimulationConfig",
    "SimulationPath",
    "SimulationList",
    "TimelineNode",
    "RoundResult",
    "AgentAction",
    "Interaction",
    "Action",
    "RedTeamChallenge",
    "Synthesis"
]
