"""
AI爬虫核心
智能多源信息收集框架
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import httpx
from loguru import logger


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    # 请求配置
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    concurrent_limit: int = 5
    
    # 内容配置
    max_content_length: int = 10000
    min_content_length: int = 100
    
    # AI配置
    use_ai_extraction: bool = True
    ai_model: str = "gpt-4"
    
    # 过滤配置
    date_range_days: int = 30
    relevance_threshold: float = 0.6


@dataclass
class RawContent:
    """原始内容"""
    source: str
    url: str
    title: str
    content: str
    published_at: Optional[datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if len(self.content) > 10000:
            self.content = self.content[:10000] + "..."


@dataclass
class ProcessedContent:
    """处理后的内容"""
    raw: RawContent
    relevance_score: float
    entities: List[Dict[str, Any]]
    summary: str
    sentiment: str
    key_facts: List[str]


class DataSource(ABC):
    """数据源抽象基类"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.http_client = httpx.AsyncClient(timeout=30)
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[RawContent]:
        """搜索内容"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass
    
    async def close(self):
        """关闭连接"""
        await self.http_client.aclose()


class AICrawler:
    """
    AI爬虫核心
    
    功能：
    1. 多源并发爬取
    2. AI智能内容提取
    3. 实体识别与关系分析
    4. 相关性评分
    5. 去重与聚合
    """
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.data_sources: List[DataSource] = []
        self.semaphore = asyncio.Semaphore(self.config.concurrent_limit)
        self._entity_extractor = None
        self._content_analyzer = None
    
    def register_source(self, source: DataSource):
        """注册数据源"""
        if source.is_available():
            self.data_sources.append(source)
            logger.info(f"Registered data source: {source.name}")
        else:
            logger.warning(f"Data source {source.name} is not available")
    
    async def crawl(
        self,
        query: str,
        filters: Dict[str, Any] = None
    ) -> List[ProcessedContent]:
        """
        执行爬取任务
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            
        Returns:
            处理后的内容列表
        """
        logger.info(f"Starting crawl for query: {query}")
        
        # 1. 并发从多个数据源收集
        raw_contents = await self._collect_from_sources(query, filters)
        logger.info(f"Collected {len(raw_contents)} raw contents")
        
        # 2. 去重
        unique_contents = self._deduplicate(raw_contents)
        logger.info(f"After deduplication: {len(unique_contents)} contents")
        logger.debug(f"{unique_contents} ")
        
        # 3. AI处理
        processed_contents = await self._process_contents(unique_contents, query)
        logger.info(f"Processed {len(processed_contents)} contents")
        
        # 4. 过滤低相关性内容
        filtered_contents = [
            c for c in processed_contents
            if c.relevance_score >= self.config.relevance_threshold
        ]
        logger.info(f"After filtering: {len(filtered_contents)} contents")
        
        # 5. 排序（按相关性）
        sorted_contents = sorted(
            filtered_contents,
            key=lambda x: x.relevance_score,
            reverse=True
        )
        
        return sorted_contents
    
    async def _collect_from_sources(
        self,
        query: str,
        filters: Dict[str, Any]
    ) -> List[RawContent]:
        """从多个数据源并发收集"""
        tasks = []
        
        for source in self.data_sources:
            task = self._crawl_with_semaphore(source, query, filters)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_contents = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Crawl error: {result}")
            else:
                all_contents.extend(result)
        
        return all_contents
    
    async def _crawl_with_semaphore(
        self,
        source: DataSource,
        query: str,
        filters: Dict[str, Any]
    ) -> List[RawContent]:
        """使用信号量限制并发"""
        async with self.semaphore:
            try:
                contents = await source.search(query, **filters)
                return contents
            except Exception as e:
                logger.error(f"Error crawling {source.name}: {e}")
                return []
    
    def _deduplicate(self, contents: List[RawContent]) -> List[RawContent]:
        """去重（基于URL和内容相似度）"""
        seen_urls = set()
        unique_contents = []
        
        for content in contents:
            # URL去重
            if content.url in seen_urls:
                continue
            seen_urls.add(content.url)
            
            # TODO: 内容相似度去重（使用文本相似度算法）
            
            unique_contents.append(content)
        
        return unique_contents
    
    async def _process_contents(
        self,
        contents: List[RawContent],
        query: str
    ) -> List[ProcessedContent]:
        """AI处理内容"""
        from .extractor import EntityExtractor
        from .analyzer import ContentAnalyzer
        
        extractor = EntityExtractor()
        analyzer = ContentAnalyzer()
        
        tasks = [
            self._process_single_content(content, query, extractor, analyzer)
            for content in contents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Processing error: {result}")
            else:
                processed.append(result)
        
        return processed
    
    async def _process_single_content(
        self,
        content: RawContent,
        query: str,
        extractor: 'EntityExtractor',
        analyzer: 'ContentAnalyzer'
    ) -> ProcessedContent:
        """处理单个内容"""
        # 并行执行提取和分析
        entities_task = extractor.extract_entities(content.content)
        analysis_task = analyzer.analyze(content.content, query)
        
        entities, analysis = await asyncio.gather(entities_task, analysis_task)
        
        return ProcessedContent(
            raw=content,
            relevance_score=analysis.get("relevance", 0.5),
            entities=entities,
            summary=analysis.get("summary", ""),
            sentiment=analysis.get("sentiment", "neutral"),
            key_facts=analysis.get("key_facts", [])
        )
    
    async def close(self):
        """关闭所有连接"""
        for source in self.data_sources:
            await source.close()
