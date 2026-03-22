"""
领域事件 (Domain Events)
用于解耦领域内的各个模块
"""
from .simulation_events import (
    SimulationStarted,
    SimulationCompleted,
    RoundCompleted,
    EntityReacted,
)
from .intelligence_events import (
    IntelligenceCollectionStarted,
    IntelligenceCollectionCompleted,
    EntitiesIdentified,
)
from .event_bus import EventBus, DomainEvent

__all__ = [
    "EventBus",
    "DomainEvent",
    "SimulationStarted",
    "SimulationCompleted",
    "RoundCompleted",
    "EntityReacted",
    "IntelligenceCollectionStarted",
    "IntelligenceCollectionCompleted",
    "EntitiesIdentified",
]
