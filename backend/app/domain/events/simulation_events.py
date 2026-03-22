"""
推演相关领域事件
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from .event_bus import DomainEvent


@dataclass
class SimulationStarted(DomainEvent):
    """推演开始事件"""
    proposition: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, simulation_id: str, proposition: str, config: Dict[str, Any] = None):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=simulation_id
        )
        self.proposition = proposition
        self.config = config or {}


@dataclass
class SimulationCompleted(DomainEvent):
    """推演完成事件"""
    status: str  # completed / failed
    result_summary: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    def __init__(self, simulation_id: str, status: str, 
                 result_summary: Dict[str, Any] = None,
                 error_message: str = None,
                 duration_seconds: float = None):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=simulation_id
        )
        self.status = status
        self.result_summary = result_summary or {}
        self.error_message = error_message
        self.duration_seconds = duration_seconds


@dataclass
class RoundCompleted(DomainEvent):
    """推演轮次完成事件"""
    round_number: int
    entity_reactions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    global_summary: str = ""
    
    def __init__(self, simulation_id: str, round_number: int,
                 entity_reactions: Dict[str, Dict[str, Any]] = None,
                 global_summary: str = ""):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=simulation_id
        )
        self.round_number = round_number
        self.entity_reactions = entity_reactions or {}
        self.global_summary = global_summary


@dataclass
class EntityReacted(DomainEvent):
    """实体反应事件"""
    entity_name: str
    round_number: int
    reaction: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, simulation_id: str, entity_name: str,
                 round_number: int, reaction: Dict[str, Any] = None):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=simulation_id
        )
        self.entity_name = entity_name
        self.round_number = round_number
        self.reaction = reaction or {}
