"""
情报收集应用服务

协调情报收集的完整流程，发布领域事件
"""
from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime
from loguru import logger

from app.domain.events import (
    event_bus,
    IntelligenceCollectionStarted,
    IntelligenceCollectionCompleted,
    EntitiesIdentified,
)
from app.infrastructure.external.llm import LLMFactory, LLMProvider
from app.infrastructure.repositories import IntelligenceRepository


class IntelligenceApplicationService:
    """
    情报收集应用服务
    
    职责：
    1. 协调情报收集流程
    2. 管理事务边界
    3. 发布领域事件
    4. 处理缓存逻辑
    """
    
    def __init__(
        self,
        repository: IntelligenceRepository,
        llm_provider: Optional[LLMProvider] = None
    ):
        self._repository = repository
        self._llm = llm_provider or LLMFactory.create_with_fallback()
    
    async def start_collection(
        self,
        query: str,
        sources: List[str] = None,
        use_cache: bool = True
    ) -> str:
        """
        启动情报收集
        
        Args:
            query: 查询命题
            sources: 数据源列表
            use_cache: 是否使用缓存
            
        Returns:
            collection_id: 收集任务ID
        """
        collection_id = str(uuid4())
        
        # 检查缓存
        if use_cache:
            cached = await self._repository.get_fresh_cache(query)
            if cached:
                logger.info(f"Using cached intelligence for: {query[:50]}...")
                return cached["id"]
        
        # 发布开始事件
        await event_bus.publish(
            IntelligenceCollectionStarted(
                collection_id=collection_id,
                query=query,
                sources=sources or ["gdelt"]
            )
        )
        
        logger.info(f"Started intelligence collection: {collection_id}")
        return collection_id
    
    async def complete_collection(
        self,
        collection_id: str,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        articles: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        完成情报收集
        
        Args:
            collection_id: 收集任务ID
            entities: 识别到的实体
            relationships: 实体关系
            articles: 收集的文章
            sources: 数据源
            query: 原始查询
            
        Returns:
            保存的情报记录
        """
        # 保存到仓储
        intelligence_record = await self._repository.add({
            "id": collection_id,
            "event_description": query,
            "identified_entities": entities,
            "pre_identified_relationships": relationships,
            "collected_articles": articles,
        })
        
        # 发布完成事件
        await event_bus.publish(
            IntelligenceCollectionCompleted(
                collection_id=collection_id,
                status="completed",
                entities_count=len(entities),
                sources_count=len(sources),
                articles_count=len(articles)
            )
        )
        
        # 发布实体识别事件
        await event_bus.publish(
            EntitiesIdentified(
                collection_id=collection_id,
                entities=entities,
                relationships=relationships,
                identification_method="llm"
            )
        )
        
        logger.info(f"Completed intelligence collection: {collection_id}")
        return intelligence_record
    
    async def get_intelligence(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """获取情报记录"""
        return await self._repository.get_by_id(collection_id)
    
    async def get_intelligence_by_query(self, query: str) -> Optional[Dict[str, Any]]:
        """根据查询获取情报"""
        return await self._repository.get_by_event_description(query)
    
    async def list_recent_intelligence(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """列出最近的情报"""
        return await self._repository.list_recent(limit=limit, offset=offset)
