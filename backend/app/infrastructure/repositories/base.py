"""
仓储基类
定义仓储接口规范
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Any
from uuid import UUID

T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """
    同步仓储接口
    
    提供领域对象的CRUD操作抽象
    """
    
    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[T]:
        """根据ID获取实体"""
        pass
    
    @abstractmethod
    def list(self, **filters) -> List[T]:
        """列出实体，支持过滤"""
        pass
    
    @abstractmethod
    def add(self, entity: T) -> T:
        """添加实体"""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """更新实体"""
        pass
    
    @abstractmethod
    def delete(self, id: UUID) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    def exists(self, id: UUID) -> bool:
        """检查实体是否存在"""
        pass


class AsyncRepository(ABC, Generic[T]):
    """
    异步仓储接口
    
    提供领域对象的异步CRUD操作抽象
    """
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """根据ID获取实体"""
        pass
    
    @abstractmethod
    async def list(self, **filters) -> List[T]:
        """列出实体，支持过滤"""
        pass
    
    @abstractmethod
    async def add(self, entity: T) -> T:
        """添加实体"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def exists(self, id: UUID) -> bool:
        """检查实体是否存在"""
        pass
    
    @abstractmethod
    async def count(self, **filters) -> int:
        """统计数量"""
        pass
