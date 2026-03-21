"""
SQLAlchemy基础模型
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    基础模型类
    所有模型都继承此类
    """
    
    # 自动生成表名（小写类名）
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # 通用字段
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
