"""
情报收集服务
负责从多源收集信息、识别实体、分析态势
集成AI爬虫框架
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from loguru import logger

from app.services.intelligence.framework.crawler import AICrawler, CrawlerConfig
from app.services.intelligence.framework.extractor import EntityExtractor
from app.services.intelligence.framework.analyzer import ContentAnalyzer
from app.services.intelligence.framework.query_expander import QueryExpander
from app.services.intelligence.sources.gdelt_source import GDELTSource
from app.services.intelligence.sources.newsapi_source import NewsAPISource
from app.services.intelligence.cache_service import IntelligenceCacheService
from app.models.intelligence_cache import IntelligenceCache


class EntityIdentification(BaseModel):
    """识别到的实体"""
    name: str
    name_en: Optional[str] = None
    entity_type: str  # country, organization, non_state_armed, etc.
    role: str  # initiator, target, ally, proxy_actor, etc.
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    current_actions: List[str] = Field(default=[])
    stated_position: Optional[str] = None
    key_interests: List[str] = Field(default=[])


class RelationshipDynamics(BaseModel):
    """关系动态"""
    active_conflicts: List[List[str]] = Field(default=[])
    tensions: List[List[str]] = Field(default=[])
    cooperation: List[List[str]] = Field(default=[])
    key_relationships: List[Dict[str, Any]] = Field(default=[])


class MilitaryDeployment(BaseModel):
    """军事部署信息"""
    actor: str
    location: str
    force_type: str
    estimated_size: Optional[str] = None
    timestamp: Optional[datetime] = None


class DiplomaticActivity(BaseModel):
    """外交活动"""
    participants: List[str]
    type: str  # meeting, statement, visit, etc.
    content: str
    timestamp: Optional[datetime] = None


class IntelligenceReport(BaseModel):
    """情报报告 - 推演输入"""
    event_summary: str
    timeframe: str
    background: str

    # 识别到的实体
    identified_entities: List[EntityIdentification]

    # 关系动态
    relationship_dynamics: RelationshipDynamics

    # 当前态势
    military_deployments: List[MilitaryDeployment] = Field(default=[])
    diplomatic_activities: List[DiplomaticActivity] = Field(default=[])
    economic_measures: List[Dict] = Field(default=[])

    # 数据来源
    sources: List[Dict] = Field(default=[])

    # 元数据
    collected_at: datetime = Field(default_factory=datetime.now)
    confidence_level: str = "medium"  # high/medium/low


class IntelligenceCollector:
    """
    情报收集器
    集成AI爬虫框架，从多源收集信息，识别实体和态势
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        # 初始化AI爬虫
        self.crawler = AICrawler(
            config=CrawlerConfig(
                timeout=30,
                max_retries=3,
                concurrent_limit=5,
                relevance_threshold=0.5,
                date_range_days=30,
                use_ai_extraction=True
            )
        )
        # 初始化提取器和分析器
        self.entity_extractor = EntityExtractor()
        self.content_analyzer = ContentAnalyzer()
        # 初始化查询扩展器
        self.query_expander = QueryExpander()
        # 注册数据源
        self._register_data_sources()
        # 用于保存最近一次收集的原始内容
        self.last_raw_contents = []
        # 用于保存预识别的实体（LLM预识别阶段）
        self.pre_identified_entities = []
        # 用于保存扩展结果
        self.last_expansion_result = None

    def _register_data_sources(self):
        """注册数据源到爬虫"""
        # GDELT - 全球事件数据库（免费，无需API key）
        gdelt_source = GDELTSource()
        self.crawler.register_source(gdelt_source)
        logger.info("Registered GDELT data source")

        # NewsAPI - 新闻聚合（需要API key）
        newsapi_source = NewsAPISource()
        if newsapi_source.is_available():
            self.crawler.register_source(newsapi_source)
            logger.info("Registered NewsAPI data source")
        else:
            logger.warning("NewsAPI not available (API key not configured)")

    async def collect(
        self, 
        event_description: str,
        use_cache: bool = True,
        db = None
    ) -> IntelligenceReport:
        """
        收集情报并生成结构化报告
        
        新流程：
        1. 检查缓存（如果启用）
        2. 智能查询扩展：将用户命题扩展为多个搜索查询
        3. 实体预识别：识别可能涉及的所有实体
        4. 并行搜索：执行多个扩展查询（支持增量更新）
        5. 实体识别与关系分析
        6. 态势理解与报告生成
        7. 保存到缓存

        Args:
            event_description: 事件描述（用户输入的命题）
            use_cache: 是否使用缓存
            db: 数据库会话（用于缓存操作）

        Returns:
            结构化的情报报告
        """
        logger.info(f"Starting intelligence collection: {event_description[:100]}...")
        
        # 检查缓存
        cache_service = None
        cached_result = None
        incremental_range = None
        
        if use_cache and db:
            cache_service = IntelligenceCacheService(db)
            cache_status = await cache_service.get_cache_status(event_description)
            
            if cache_status["is_fresh"]:
                # 缓存新鲜，直接返回
                logger.info("Using fresh cache for this query")
                cached_result = cache_status["cache"]
                return self._cache_to_report(cached_result)
            
            elif cache_status["needs_incremental"]:
                # 需要增量更新
                logger.info("Cache needs incremental update")
                cached_result = cache_status["cache"]
                incremental_range = await cache_service.get_incremental_date_range(event_description)
        
        # Step 0: 智能查询扩展和实体预识别（如果尚未完成）
        if not self.pre_identified_entities:
            logger.info("Step 0: Expanding query and pre-identifying entities...")
            expansion_result = await self.query_expander.expand_query(event_description)
            
            logger.info(f"Expanded into {len(expansion_result.expanded_queries)} queries:")
            for q in expansion_result.expanded_queries:
                logger.info(f"  [{q.query_type}] {q.query} (priority: {q.priority})")
            
            logger.info(f"Pre-identified {len(expansion_result.pre_identified_entities)} entities:")
            for e in expansion_result.pre_identified_entities[:10]:  # 只显示前10个
                logger.info(f"  {e.name} ({e.entity_type}) - {e.role} - relevance: {e.relevance}")
            
            # 保存预识别实体供前端展示
            self.pre_identified_entities = [
                {
                    "name": e.name,
                    "name_en": e.name_en,
                    "entity_type": e.entity_type,
                    "role": e.role,
                    "relevance": e.relevance,
                    "rationale": e.rationale,
                    "key_interests": e.key_interests
                }
                for e in expansion_result.pre_identified_entities
            ]
            
            # 保存关系数据
            self.pre_identified_relationships = expansion_result.relationships if hasattr(expansion_result, 'relationships') else []
            
            # 保存扩展结果供后续使用
            self.last_expansion_result = expansion_result
        else:
            logger.info("Using pre-existing pre-identified entities")
            # 从已保存的数据重建expansion_result
            from app.services.intelligence.framework.query_expander import QueryExpansionResult, ExpandedQuery, PreIdentifiedEntity
            
            entities = [
                PreIdentifiedEntity(
                    name=e["name"],
                    entity_type=e["entity_type"],
                    role=e["role"],
                    relevance=e["relevance"],
                    rationale=e.get("rationale", ""),
                    key_interests=e.get("key_interests", [])
                )
                for e in self.pre_identified_entities
            ]
            
            queries = []
            if self.last_expansion_result:
                queries = self.last_expansion_result.expanded_queries
            
            expansion_result = QueryExpansionResult(
                original_query=event_description,
                expanded_queries=queries,
                pre_identified_entities=entities,
                relationships=self.pre_identified_relationships
            )

        # Step 1: 使用AI爬虫从多源收集数据（使用扩展的查询）
        # 如果有增量更新范围，只获取新文章
        if incremental_range:
            logger.info(f"Incremental update: fetching articles from {incremental_range['start_date']} to {incremental_range['end_date']}")
            new_contents = await self._crawl_intelligence_with_expansion(
                expansion_result,
                date_range=incremental_range
            )
            # 合并缓存的文章和新文章
            cached_articles = cached_result.collected_articles or []
            processed_contents = self._merge_contents(cached_articles, new_contents)
        else:
            processed_contents = await self._crawl_intelligence_with_expansion(expansion_result)
        
        # 保存原始内容供API使用
        self.last_raw_contents = processed_contents

        # Step 2: 实体识别与关系分析（结合预识别结果）
        entities, relationships = await self._analyze_entities_and_relations(
            event_description,
            processed_contents,
            expansion_result.pre_identified_entities,
            expansion_result.relationships
        )

        # Step 3: 态势理解
        situation = await self._understand_situation(event_description, processed_contents)

        # Step 4: 整合为情报报告
        report = IntelligenceReport(
            event_summary=await self._generate_summary(event_description, processed_contents),
            timeframe="current",
            background=await self._extract_background(processed_contents),
            identified_entities=entities,
            relationship_dynamics=relationships,
            military_deployments=situation.get("military", []),
            diplomatic_activities=situation.get("diplomatic", []),
            economic_measures=situation.get("economic", []),
            sources=self._format_sources(processed_contents),
            confidence_level=self._calculate_confidence(processed_contents, entities)
        )

        # Step 5: 保存到缓存
        if cache_service:
            logger.info(f"Saving results to cache for: {event_description[:50]}...")
            try:
                await self._save_to_cache(cache_service, event_description, report, processed_contents)
                logger.info("Results saved to cache successfully")
            except Exception as e:
                logger.error(f"Failed to save to cache: {e}")
        else:
            logger.warning("Cache service not available, results will not be cached")

        logger.info(f"Intelligence collection completed. Identified {len(entities)} entities.")
        return report
    
    def _cache_to_report(self, cache: IntelligenceCache) -> IntelligenceReport:
        """将缓存转换为情报报告"""
        from app.services.intelligence.framework.query_expander import PreIdentifiedEntity
        
        # 恢复预识别实体
        self.pre_identified_entities = cache.pre_identified_entities or []
        self.pre_identified_relationships = cache.pre_identified_relationships or []
        
        # 转换实体格式
        entities = [
            EntityIdentification(
                name=e.get("name", ""),
                name_en=e.get("name_en"),
                entity_type=e.get("entity_type", "unknown"),
                role=e.get("role", "unknown"),
                relevance_score=e.get("relevance_score", 0.5),
                current_actions=e.get("current_actions", []),
                stated_position=e.get("stated_position", ""),
                key_interests=e.get("key_interests", [])
            )
            for e in (cache.identified_entities or [])
        ]
        
        # 转换关系动态
        rel_dynamics = cache.relationship_dynamics or {}
        relationships = RelationshipDynamics(
            active_conflicts=rel_dynamics.get("active_conflicts", []),
            tensions=rel_dynamics.get("tensions", []),
            cooperation=rel_dynamics.get("cooperation", []),
            key_relationships=rel_dynamics.get("key_relationships", [])
        )
        
        return IntelligenceReport(
            event_summary=cache.event_description,
            timeframe="current",
            background="",
            identified_entities=entities,
            relationship_dynamics=relationships,
            military_deployments=[],
            diplomatic_activities=[],
            economic_measures=[],
            sources=[],
            confidence_level="high"
        )
    
    async def _save_to_cache(
        self,
        cache_service: IntelligenceCacheService,
        event_description: str,
        report: IntelligenceReport,
        processed_contents: List[Any]
    ):
        """保存结果到缓存"""
        try:
            # 格式化文章数据
            articles = [
                {
                    "source": content.raw.source,
                    "title": content.raw.title,
                    "url": content.raw.url,
                    "published_at": content.raw.published_at.isoformat() if content.raw.published_at else None,
                    "relevance_score": content.relevance_score,
                    "sentiment": content.sentiment,
                    "summary": content.summary
                }
                for content in processed_contents[:50]  # 限制数量
            ]
            
            # 格式化实体数据
            entities = [
                {
                    "name": e.name,
                    "name_en": e.name_en,
                    "entity_type": e.entity_type,
                    "role": e.role,
                    "relevance_score": e.relevance_score,
                    "current_actions": e.current_actions,
                    "stated_position": e.stated_position,
                    "key_interests": e.key_interests
                }
                for e in report.identified_entities
            ]
            
            # 格式化扩展查询
            expanded_queries = []
            if self.last_expansion_result:
                expanded_queries = [
                    {
                        "query": q.query,
                        "query_type": q.query_type,
                        "rationale": q.rationale,
                        "priority": q.priority
                    }
                    for q in self.last_expansion_result.expanded_queries
                ]
            
            # 获取最后文章日期
            last_article_date = None
            if processed_contents:
                dates = [c.raw.published_at for c in processed_contents if c.raw.published_at]
                if dates:
                    last_article_date = max(dates)
            
            await cache_service.save_cache(
                event_description=event_description,
                pre_identified_entities=self.pre_identified_entities,
                pre_identified_relationships=self.pre_identified_relationships,
                expanded_queries=expanded_queries,
                collected_articles=articles,
                identified_entities=entities,
                relationship_dynamics={
                    "active_conflicts": report.relationship_dynamics.active_conflicts,
                    "tensions": report.relationship_dynamics.tensions,
                    "cooperation": report.relationship_dynamics.cooperation,
                    "key_relationships": getattr(report.relationship_dynamics, 'key_relationships', [])
                },
                last_article_date=last_article_date
            )
            
            logger.info("Saved results to cache")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _merge_contents(self, cached_articles: List[Dict], new_contents: List[Any]) -> List[Any]:
        """合并缓存的文章和新收集的文章"""
        # 这里简化处理，实际应该根据URL去重
        # 返回新内容，让后续处理决定如何使用缓存数据
        return new_contents

    async def _crawl_intelligence(self, event_description: str) -> List[Any]:
        """
        使用AI爬虫从多源收集情报（旧方法，保留兼容）
        """
        return await self._crawl_intelligence_with_expansion(
            type('obj', (object,), {
                'original_query': event_description,
                'expanded_queries': [type('q', (object,), {
                    'query': event_description,
                    'query_type': 'original',
                    'priority': 1
                })],
                'pre_identified_entities': []
            })()
        )
    
    async def _crawl_intelligence_with_expansion(self, expansion_result, date_range: Optional[Dict] = None) -> List[Any]:
        """
        迭代递归式情报收集
        
        策略：
        1. 执行基础扩展查询，收集初始内容
        2. 从内容中提取实体，识别新实体
        3. 对新实体进行专项搜索（事件对该实体的影响）
        4. 重复步骤2-3，直到没有新实体或达到最大迭代次数
        5. 整合所有内容，按实体分类整理
        
        Args:
            expansion_result: 查询扩展结果
            date_range: 可选的日期范围限制（用于增量更新）
            
        Returns:
            处理后的内容列表
        """
        try:
            all_contents = []
            discovered_entities = {}  # 已发现的实体，使用字典存储完整信息
            max_iterations = 3  # 最大迭代次数
            
            # 构建filters，如果提供了date_range则使用它
            filters = {
                "max_records": 20,
                "date_range_days": 30
            }
            if date_range:
                filters["date_range"] = date_range
            
            # 初始化：添加预识别的实体
            # 使用字典存储，键是实体名称，值包含完整信息（包括name_en）
            for entity in expansion_result.pre_identified_entities:
                entity_name = entity.name if hasattr(entity, 'name') else entity.get('name', '')
                if entity_name:
                    discovered_entities[entity_name] = {
                        'name': entity_name,
                        'name_en': entity.name_en if hasattr(entity, 'name_en') else entity.get('name_en'),
                        'entity_type': entity.entity_type if hasattr(entity, 'entity_type') else entity.get('entity_type', 'unknown'),
                        'role': entity.role if hasattr(entity, 'role') else entity.get('role', 'unknown')
                    }
            
            logger.info(f"Starting with {len(discovered_entities)} pre-identified entities")
            
            # ===== 第1轮：基础扩展查询 =====
            logger.info("=== Round 1: Base expanded queries ===")
            sorted_queries = sorted(
                expansion_result.expanded_queries,
                key=lambda q: q.priority
            )
            
            for query_item in sorted_queries:
                # 使用英文查询进行搜索（GDELT对英文支持更好）
                search_query = getattr(query_item, 'query_en', None) or query_item.query
                logger.info(f"Searching: {search_query} (EN) / {query_item.query} (CN)")
                try:
                    contents = await self.crawler.crawl(
                        query=search_query,
                        filters=filters
                    )
                    logger.info(f"  Found {len(contents)} contents")
                    all_contents.extend(contents)
                    
                    # 从内容中提取新实体
                    new_entities = await self._extract_entities_from_contents(contents)
                    for entity_name in new_entities:
                        if entity_name not in discovered_entities:
                            discovered_entities[entity_name] = {'name': entity_name}
                            logger.info(f"  Discovered new entity: {entity_name}")
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"  Failed to search '{query_item.query}': {e}")
                    continue
            
            # ===== 迭代轮次：对新实体进行专项搜索 =====
            for iteration in range(2, max_iterations + 1):
                logger.info(f"=== Round {iteration}: Entity-specific searches ===")
                
                # 获取本轮要搜索的实体（排除已搜索过的）
                entities_to_search = list(discovered_entities.values())[:10]  # 限制数量，获取字典的值（完整实体信息）
                new_entities_found = False
                
                for entity in entities_to_search:
                    # 获取实体名称（优先使用英文名称，GDELT对英文支持更好）
                    entity_name = entity.get('name', '') if isinstance(entity, dict) else getattr(entity, 'name', '')
                    entity_name_en = entity.get('name_en') if isinstance(entity, dict) else getattr(entity, 'name_en', None)
                    
                    # 优先使用英文名称（如果存在且长度合适）
                    search_term = entity_name_en if entity_name_en and len(entity_name_en) > 2 else entity_name
                    
                    # 构建英文查询：事件对该实体的影响
                    # 使用英文关键词，GDELT对英文支持更好
                    impact_query = f"{expansion_result.original_query} {search_term} impact analysis"
                    logger.info(f"Searching impact on {entity_name} ({search_term}): {impact_query}")
                    
                    try:
                        # 使用相同的filters（包含date_range如果提供）
                        entity_filters = filters.copy()
                        entity_filters["max_records"] = 10
                        contents = await self.crawler.crawl(
                            query=impact_query,
                            filters=entity_filters
                        )
                        
                        if contents:
                            logger.info(f"  Found {len(contents)} contents about {entity_name}")
                            all_contents.extend(contents)
                            
                            # 从内容中提取更多实体
                            new_entities = await self._extract_entities_from_contents(contents)
                            for new_entity in new_entities:
                                if new_entity not in discovered_entities:
                                    discovered_entities.add(new_entity)
                                    logger.info(f"  Discovered new entity from content: {new_entity}")
                                    new_entities_found = True
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.warning(f"  Failed to search impact on '{entity_name}': {e}")
                        continue
                
                # 如果没有发现新实体，提前结束迭代
                if not new_entities_found:
                    logger.info("No new entities discovered, ending iteration")
                    break
            
            logger.info(f"Total discovered entities: {len(discovered_entities)}")
            logger.info(f"Total collected contents: {len(all_contents)}")
            
            # 保存发现的实体列表供后续使用
            self.discovered_entities = list(discovered_entities)
            
            # 去重和排序
            seen_urls = set()
            unique_contents = []
            for content in all_contents:
                url = content.raw.url
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_contents.append(content)
            
            # 按相关性排序
            sorted_contents = sorted(
                unique_contents,
                key=lambda x: x.relevance_score,
                reverse=True
            )
            
            final_contents = sorted_contents[:50]
            logger.info(f"Final unique content count: {len(final_contents)}")
            
            return final_contents
            
        except Exception as e:
            logger.error(f"Crawl error: {e}")
            return []
    
    async def _extract_entities_from_contents(self, contents: List[Any]) -> set:
        """
        从内容列表中快速提取实体名称
        
        使用简单的启发式方法，避免调用LLM导致阻塞
        
        Args:
            contents: 内容列表
            
        Returns:
            实体名称集合
        """
        entities = set()
        
        # 从标题中提取可能的实体（使用简单规则）
        for content in contents[:5]:
            title = content.raw.title if hasattr(content, 'raw') else ''
            if not title:
                continue
            
            # 简单的启发式：提取大写的连续字符（可能是专有名词）
            import re
            # 匹配2-15个字符的中文或英文单词
            potential_entities = re.findall(r'[\u4e00-\u9fa5]{2,15}|[A-Z][a-zA-Z\s]{1,20}', title)
            for entity in potential_entities:
                entity_clean = entity.strip()
                if entity_clean and len(entity_clean) > 1:
                    entities.add(entity_clean)
        
        return entities

    async def _analyze_entities_and_relations(
        self,
        event_description: str,
        processed_contents: List[Any],
        pre_identified_entities: List[Any] = None,
        pre_identified_relationships: List[Any] = None
    ) -> tuple[List[EntityIdentification], RelationshipDynamics]:
        """
        分析识别实体和关系
        
        新方法：结合预识别的实体和内容分析的结果

        Args:
            event_description: 事件描述
            processed_contents: 处理后的内容列表
            pre_identified_entities: 预识别的实体列表（可选）
            pre_identified_relationships: 预识别的关系列表（可选）

        Returns:
            实体列表和关系动态
        """
        # 如果没有内容但有预识别实体，直接使用预识别实体
        if not processed_contents:
            if pre_identified_entities:
                logger.info(f"No content collected, using {len(pre_identified_entities)} pre-identified entities")
                merged_entities = []
                for pre_entity in pre_identified_entities:
                    # PreIdentifiedEntity 是对象，使用属性访问
                    name = getattr(pre_entity, 'name', None)
                    if name:
                        merged_entities.append({
                            "name": name,
                            "name_en": getattr(pre_entity, 'name_en', None),
                            "entity_type": getattr(pre_entity, 'entity_type', 'unknown'),
                            "role": getattr(pre_entity, 'role', 'unknown'),
                            "relevance_score": getattr(pre_entity, 'relevance', 0.5),
                            "rationale": getattr(pre_entity, 'rationale', None),
                            "key_interests": getattr(pre_entity, 'key_interests', []),
                            "source": "pre_identified"
                        })
                
                # 构建关系动态
                relationship_dynamics = RelationshipDynamics()
                if pre_identified_relationships:
                    relationship_dynamics.key_relationships = pre_identified_relationships
                
                logger.info(f"Returning {len(merged_entities)} entities from pre-identification")
                return merged_entities, relationship_dynamics
            else:
                logger.warning("No content to analyze and no pre-identified entities, returning empty")
                return [], RelationshipDynamics()

        # 合并所有内容用于实体提取
        combined_text = "\n\n".join([
            f"Title: {content.raw.title}\nContent: {content.raw.content}"
            for content in processed_contents[:10]  # 限制前10条
        ])

        # 提取实体（从内容中）
        extracted_entities = await self.entity_extractor.extract_entities(combined_text)
        logger.info(f"Extracted {len(extracted_entities)} entities from content")
        
        # 合并预识别的实体和提取的实体
        all_entity_names = set()
        merged_entities = []
        
        # 首先添加预识别的实体
        if pre_identified_entities:
            logger.info(f"Merging {len(pre_identified_entities)} pre-identified entities")
            for pre_entity in pre_identified_entities:
                # PreIdentifiedEntity 是对象，使用属性访问
                name = getattr(pre_entity, 'name', None)
                if name and name not in all_entity_names:
                    all_entity_names.add(name)
                    merged_entities.append({
                        "name": name,
                        "name_en": getattr(pre_entity, 'name_en', None),
                        "entity_type": getattr(pre_entity, 'entity_type', 'unknown'),
                        "role": getattr(pre_entity, 'role', 'unknown'),
                        "relevance_score": getattr(pre_entity, 'relevance', 0.5),
                        "source": "pre_identified"
                    })
        
        # 然后添加从内容中提取的实体
        for entity_data in extracted_entities:
            if not entity_data or not isinstance(entity_data, dict):
                continue
            name = entity_data.get("name", "")
            if name and name not in all_entity_names:
                all_entity_names.add(name)
                merged_entities.append({
                    **entity_data,
                    "source": "extracted"
                })
        
        logger.info(f"Total merged entities: {len(merged_entities)}")

        # 提取关系
        relationships_data = await self.entity_extractor.extract_relationships(
            combined_text,
            merged_entities
        )

        # 分析每个实体的角色（使用批量处理优化性能）
        logger.info(f"Analyzing roles for {len(merged_entities)} entities using batch processing...")
        
        # 批量分析实体角色
        role_analyses = await self.entity_extractor.analyze_entity_roles_batch(
            entities=merged_entities,
            event_description=event_description,
            context=combined_text
        )
        
        entities = []
        for i, entity_data in enumerate(merged_entities):
            if not entity_data or not isinstance(entity_data, dict):
                continue
            entity_name = entity_data.get("name", "")
            if not entity_name:
                continue

            # 获取对应的角色分析结果
            role_analysis = role_analyses[i] if i < len(role_analyses) else {
                "role": "unknown",
                "relevance_score": 0.5,
                "current_actions": [],
                "stated_position": "",
                "key_interests": []
            }

            entity = EntityIdentification(
                name=entity_name,
                name_en=entity_data.get("name_en"),
                entity_type=entity_data.get("entity_type", "unknown"),
                role=role_analysis.get("role", "unknown"),
                relevance_score=role_analysis.get("relevance_score", role_analysis.get("relevance", 0.5)),
                current_actions=role_analysis.get("current_actions", []),
                stated_position=role_analysis.get("stated_position", ""),
                key_interests=role_analysis.get("key_interests", [])
            )
            entities.append(entity)
            
        logger.info(f"Completed role analysis for {len(entities)} entities")

        # 按相关性排序
        entities.sort(key=lambda x: x.relevance_score, reverse=True)

        # 构建关系动态
        relationships = RelationshipDynamics(
            active_conflicts=relationships_data.get("adversaries", []),
            tensions=relationships_data.get("adversaries", []),
            cooperation=relationships_data.get("allies", []),
            key_relationships=relationships_data.get("key_relationships", [])
        )

        return entities, relationships

    async def _understand_situation(
        self,
        event_description: str,
        processed_contents: List[Any]
    ) -> Dict[str, Any]:
        """
        理解当前态势
        包括军事部署、外交活动、经济措施等
        """
        if not processed_contents:
            return {"military": [], "diplomatic": [], "economic": []}

        # 提取关键事件
        combined_text = "\n\n".join([
            f"Title: {content.raw.title}\nContent: {content.raw.content}"
            for content in processed_contents[:5]
        ])

        key_events = await self.content_analyzer.extract_key_events(combined_text)

        # 分类事件
        military = []
        diplomatic = []
        economic = []

        for event in key_events:
            if not event or not isinstance(event, dict):
                continue
            action = event.get("action", "").lower()
            event_data = {
                "actor": event.get("actor", ""),
                "action": event.get("action", ""),
                "target": event.get("target", ""),
                "significance": event.get("significance", "medium")
            }

            if any(word in action for word in ["deploy", "military", "attack", "strike", "force"]):
                military.append(event_data)
            elif any(word in action for word in ["sanction", "trade", "economic", "tariff"]):
                economic.append(event_data)
            else:
                diplomatic.append(event_data)

        return {
            "military": military,
            "diplomatic": diplomatic,
            "economic": economic,
            "key_events": key_events
        }

    async def _generate_summary(
        self,
        event_description: str,
        processed_contents: List[Any]
    ) -> str:
        """生成事件摘要"""
        if not processed_contents:
            return event_description

        # 使用内容分析器生成摘要
        contents_text = [content.raw.content for content in processed_contents[:5]]
        summary = await self.content_analyzer.summarize_multiple(
            contents_text,
            max_length=300
        )
        return summary

    async def _extract_background(self, processed_contents: List[Any]) -> str:
        """提取背景信息"""
        if not processed_contents:
            return ""

        # 合并高相关性内容作为背景
        high_relevance = [
            content for content in processed_contents
            if content.relevance_score >= 0.7
        ]

        if not high_relevance:
            high_relevance = processed_contents[:3]

        background_parts = []
        for content in high_relevance:
            background_parts.append(f"{content.raw.title}: {content.summary}")

        return "\n".join(background_parts)

    def _format_sources(self, processed_contents: List[Any]) -> List[Dict]:
        """格式化数据源信息"""
        sources = []
        seen_urls = set()

        for content in processed_contents:
            url = content.raw.url
            if url in seen_urls:
                continue
            seen_urls.add(url)

            sources.append({
                "name": content.raw.source,
                "url": url,
                "title": content.raw.title,
                "published_at": content.raw.published_at.isoformat() if content.raw.published_at else None,
                "relevance_score": content.relevance_score,
                "sentiment": content.sentiment,
                "metadata": content.raw.metadata
            })

        return sources

    def _calculate_confidence(
        self,
        processed_contents: List[Any],
        entities: List[EntityIdentification]
    ) -> str:
        """计算置信度级别"""
        if not processed_contents or not entities:
            return "low"

        # 基于内容数量和实体相关性计算
        avg_relevance = sum(c.relevance_score for c in processed_contents) / len(processed_contents)
        content_count = len(processed_contents)
        entity_count = len(entities)

        if avg_relevance >= 0.7 and content_count >= 10 and entity_count >= 3:
            return "high"
        elif avg_relevance >= 0.5 and content_count >= 5 and entity_count >= 2:
            return "medium"
        else:
            return "low"

    async def analyze_entity_impacts(
        self,
        event_description: str,
        entities: List[EntityIdentification],
        processed_contents: List[Any]
    ) -> Dict[str, Dict]:
        """
        分析事件对每个实体的影响、趋势和应对策略
        
        Args:
            event_description: 事件描述
            entities: 识别的实体列表
            processed_contents: 处理后的内容列表
            
        Returns:
            实体影响分析结果
        """
        logger.info(f"Analyzing impacts for {len(entities)} entities...")
        
        entity_impacts = {}
        
        # 为每个实体构建相关内容
        for entity in entities:
            # 筛选与该实体相关的内容
            entity_contents = [
                c for c in processed_contents
                if entity.name in c.raw.title or entity.name in c.raw.content
            ]
            
            if not entity_contents:
                continue
            
            # 合并相关内容
            combined_text = "\n\n".join([
                f"Title: {c.raw.title}\nSummary: {c.summary}"
                for c in entity_contents[:5]
            ])
            
            # 使用LLM分析该实体的影响
            prompt = f"""
事件：{event_description}
分析对象：{entity.name}（{entity.entity_type}）

相关新闻内容：
{combined_text}

请分析该事件对{entity.name}的影响：

输出JSON格式：
{{
  "impact_level": "high|medium|low",  // 影响程度
  "impact_summary": "简要描述对该实体的主要影响",
  "trends": ["趋势1", "趋势2", "趋势3"],  // 可能的发展趋势
  "response_strategies": ["策略1", "策略2", "策略3"],  // 可能的应对策略
  "key_concerns": ["关切1", "关切2"],  // 主要关切点
  "opportunities": ["机会1", "机会2"]  // 可能存在的机会
}}
"""
            
            try:
                if self.llm_client:
                    response = await self.llm_client.chat.completions.create(
                        model=settings.OPENAI_MODEL or "gpt-4-turbo-preview",
                        messages=[
                            {"role": "system", "content": "你是地缘政治影响分析专家。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=1000
                    )
                    
                    result_text = response.choices[0].message.content
                    
                    # 解析JSON
                    try:
                        import json
                        import re
                        result = json.loads(result_text)
                    except json.JSONDecodeError:
                        # 尝试从文本中提取JSON
                        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group())
                        else:
                            result = {}
                    
                    entity_impacts[entity.name] = {
                        "entity_id": entity.name,
                        "entity_type": entity.entity_type,
                        "role": entity.role,
                        **result
                    }
                    
                    logger.info(f"Analyzed impact on {entity.name}: {result.get('impact_level', 'unknown')}")
                
            except Exception as e:
                logger.warning(f"Failed to analyze impact on {entity.name}: {e}")
                entity_impacts[entity.name] = {
                    "entity_id": entity.name,
                    "entity_type": entity.entity_type,
                    "role": entity.role,
                    "impact_level": "unknown",
                    "impact_summary": "分析失败",
                    "trends": [],
                    "response_strategies": [],
                    "key_concerns": [],
                    "opportunities": []
                }
        
        return entity_impacts

    async def close(self):
        """关闭资源"""
        await self.crawler.close()
