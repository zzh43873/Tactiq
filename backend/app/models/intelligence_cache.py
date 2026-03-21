"""
情报缓存模型
用于存储和复用情报收集结果，支持增量更新
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.base import Base


class IntelligenceCache(Base):
    """
    情报缓存
    
    存储情报收集的结果，支持：
    1. 相同查询的缓存复用
    2. 增量更新（只获取新文章）
    3. 历史记录查询
    """
    
    __tablename__ = "intelligence_cache"
    
    # 查询哈希（SHA256 of normalized query）
    query_hash = Column(String(64), unique=True, nullable=False, index=True, comment="查询哈希")
    
    # 原始查询
    event_description = Column(Text, nullable=False, comment="事件描述")
    
    # 预识别实体（LLM预识别阶段）
    pre_identified_entities = Column(JSON, default=list, comment="预识别实体列表")
    
    # 预识别关系
    pre_identified_relationships = Column(JSON, default=list, comment="预识别关系列表")
    
    # 扩展查询
    expanded_queries = Column(JSON, default=list, comment="扩展查询列表")
    
    # 收集的文章
    collected_articles = Column(JSON, default=list, comment="收集的文章列表")
    
    # 最终识别的实体
    identified_entities = Column(JSON, default=list, comment="最终识别的实体列表")
    
    # 关系动态
    relationship_dynamics = Column(JSON, default=dict, comment="关系动态")
    
    # 推演结果（完整的推演输出，包含因果路径等）
    simulation_result = Column(JSON, default=None, comment="推演结果")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    # 用于增量更新的最后文章日期
    last_article_date = Column(DateTime(timezone=True), nullable=True, comment="最后文章日期")
    
    # 缓存命中次数
    hit_count = Column(Integer, default=0, comment="命中次数")
    
    # 访问时间（用于LRU淘汰）
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), comment="最后访问时间")
    
    def __repr__(self) -> str:
        return f"<IntelligenceCache(id={self.id}, query_hash={self.query_hash[:8]}..., hit_count={self.hit_count})>"
    
    def is_fresh(self, max_age_hours: int = 24) -> bool:
        """
        检查缓存是否新鲜
        
        Args:
            max_age_hours: 最大缓存时间（小时）
            
        Returns:
            如果缓存未过期返回True
        """
        if not self.updated_at:
            return False
        
        age = datetime.now(self.updated_at.tzinfo) - self.updated_at
        return age.total_seconds() < max_age_hours * 3600
    
    def needs_incremental_update(self) -> bool:
        """
        检查是否需要增量更新
        
        如果缓存是昨天的，只需要获取今天的新文章
        """
        if not self.updated_at:
            return False
        
        now = datetime.now(self.updated_at.tzinfo)
        age = now - self.updated_at
        
        # 如果缓存超过1天但小于7天，需要增量更新
        return 24 * 3600 < age.total_seconds() < 7 * 24 * 3600
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        # 检查是否有有效的推演结果（有paths且不为空）
        has_valid_simulation = (
            self.simulation_result is not None and 
            isinstance(self.simulation_result, dict) and
            self.simulation_result.get('paths') and
            len(self.simulation_result.get('paths', [])) > 0
        )
        
        return {
            "id": str(self.id),
            "event_description": self.event_description,
            "pre_identified_entities": self.pre_identified_entities,
            "pre_identified_relationships": self.pre_identified_relationships,
            "expanded_queries": self.expanded_queries,
            "identified_entities": self.identified_entities,
            "relationship_dynamics": self.relationship_dynamics,
            "simulation_result": self.simulation_result,
            "has_simulation": has_valid_simulation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "hit_count": self.hit_count,
            "article_count": len(self.collected_articles) if self.collected_articles else 0
        }
