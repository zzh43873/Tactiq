"""
领域事件总线
支持同步和异步事件订阅与发布
"""
from abc import ABC, abstractmethod
from typing import Type, List, Callable, Dict, Any, TypeVar
from dataclasses import dataclass
from datetime import datetime
import asyncio
from loguru import logger


T = TypeVar('T', bound='DomainEvent')


@dataclass
class DomainEvent:
    """领域事件基类"""
    event_id: str
    timestamp: datetime
    aggregate_id: str
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


class EventHandler(ABC):
    """事件处理器接口"""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        pass


class EventBus:
    """
    领域事件总线
    
    支持:
    - 同步/异步处理器
    - 事件订阅与发布
    - 处理器错误隔离
    """
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}
        self._async_handlers: Dict[Type[DomainEvent], List[Callable]] = {}
    
    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """
        订阅同步处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed sync handler for {event_type.__name__}")
    
    def subscribe_async(self, event_type: Type[T], handler: Callable[[T], Any]) -> None:
        """
        订阅异步处理器
        
        Args:
            event_type: 事件类型
            handler: 异步处理函数
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)
        logger.debug(f"Subscribed async handler for {event_type.__name__}")
    
    async def publish(self, event: DomainEvent) -> None:
        """
        发布事件
        
        依次执行所有处理器，错误隔离
        """
        event_type = type(event)
        
        # 执行同步处理器
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type.__name__}: {e}")
                    # 错误隔离，继续执行其他处理器
        
        # 执行异步处理器
        if event_type in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event_type]:
                try:
                    task = handler(event)
                    if asyncio.iscoroutine(task):
                        tasks.append(task)
                except Exception as e:
                    logger.error(f"Error preparing async handler for {event_type.__name__}: {e}")
            
            if tasks:
                # 并发执行所有异步处理器
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error in async handler {i} for {event_type.__name__}: {result}")
    
    def unsubscribe(self, event_type: Type[T], handler: Callable) -> None:
        """取消订阅"""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
        if event_type in self._async_handlers:
            self._async_handlers[event_type] = [
                h for h in self._async_handlers[event_type] if h != handler
            ]


# 全局事件总线实例
event_bus = EventBus()
