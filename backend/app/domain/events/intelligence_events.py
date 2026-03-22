"""
情报收集相关领域事件
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from .event_bus import DomainEvent


@dataclass
class IntelligenceCollectionStarted(DomainEvent):
    """情报收集开始事件"""
    query: str
    sources: List[str] = field(default_factory=list)
    
    def __init__(self, collection_id: str, query: str, sources: List[str] = None):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=collection_id
        )
        self.query = query
        self.sources = sources or []


@dataclass
class IntelligenceCollectionCompleted(DomainEvent):
    """情报收集完成事件"""
    status: str  # completed / failed
    entities_count: int = 0
    sources_count: int = 0
    articles_count: int = 0
    error_message: Optional[str] = None
    
    def __init__(self, collection_id: str, status: str,
                 entities_count: int = 0,
                 sources_count: int = 0,
                 articles_count: int = 0,
                 error_message: str = None):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=collection_id
        )
        self.status = status
        self.entities_count = entities_count
        self.sources_count = sources_count
        self.articles_count = articles_count
        self.error_message = error_message


@dataclass
class EntitiesIdentified(DomainEvent):
    """实体识别完成事件"""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    identification_method: str = "llm"  # llm / cache / manual
    
    def __init__(self, collection_id: str, 
                 entities: List[Dict[str, Any]] = None,
                 relationships: List[Dict[str, Any]] = None,
                 identification_method: str = "llm"):
        super().__init__(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            aggregate_id=collection_id
        )
        self.entities = entities or []
        self.relationships = relationships or []
        self.identification_method = identification_method
