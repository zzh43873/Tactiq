"""
GDELT数据源
全球事件、语言和语调数据库
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import json
import httpx
from loguru import logger

from app.services.intelligence.framework.crawler import DataSource, RawContent


class GDELTSource(DataSource):
    """
    GDELT数据源
    
    GDELT (Global Database of Events, Language, and Tone)
    是世界上最大的事件数据库，监控全球100+语言的新闻媒体
    
    特点：
    - 实时更新（每15分钟）
    - 覆盖全球100+国家
    - 支持多语言
    - 包含事件、情感、网络分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("GDELT", config)
        self.base_url = "https://api.gdeltproject.org/api/v2"
        self.doc_api_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.gkg_api_url = "https://api.gdeltproject.org/api/v2/gkg/gkg"
    
    def is_available(self) -> bool:
        """GDELT不需要API key，始终可用"""
        return True
    
    async def search(
        self,
        query: str,
        **kwargs
    ) -> List[RawContent]:
        """
        搜索GDELT数据
        
        Args:
            query: 搜索关键词
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            max_records: 最大返回记录数
            
        Returns:
            原始内容列表
        """
        max_records = kwargs.get('max_records', 50)
        
        # 构建时间范围
        end_date = kwargs.get('end_date') or datetime.now()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        start_date = kwargs.get('start_date') or (end_date - timedelta(days=7))
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        try:
            # 使用GDELT Doc API搜索新闻
            contents = await self._search_news_with_content(
                query,
                start_date,
                end_date,
                max_records
            )
            
            logger.info(f"GDELT found {len(contents)} articles for '{query}'")
            return contents
            
        except json.JSONDecodeError as e:
            logger.error(f"GDELT JSON decode error: {e}")
            return []
        except Exception as e:
            logger.error(f"GDELT search error: {type(e).__name__}: {e}")
            return []
    
    async def _search_news_with_content(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        max_records: int
    ) -> List[RawContent]:
        """搜索新闻文章并尝试获取完整内容"""
        # 先获取基础信息
        basic_contents = await self._search_news_basic(query, start_date, end_date, max_records)
        
        # 尝试获取完整内容（并发限制）
        semaphore = asyncio.Semaphore(3)  # 限制并发数
        
        async def enhance_content(content: RawContent) -> RawContent:
            async with semaphore:
                if content.url and content.content.strip() == "":
                    full_content = await self._fetch_article_content(content.url)
                    if full_content:
                        content.content = full_content
                return content
        
        # 并发增强内容
        enhanced_tasks = [enhance_content(content) for content in basic_contents]
        enhanced_contents = await asyncio.gather(*enhanced_tasks, return_exceptions=True)
        
        # 过滤异常结果
        valid_contents = []
        for content in enhanced_contents:
            if isinstance(content, Exception):
                logger.warning(f"Content enhancement failed: {content}")
            else:
                valid_contents.append(content)
        
        return valid_contents
    
    async def _search_news_basic(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        max_records: int
    ) -> List[RawContent]:
        """搜索新闻文章基础信息"""
        contents = []
        
        # GDELT Doc API参数
        params = {
            "query": query,
            "mode": "ArtList",  # 文章列表模式
            "maxrecords": min(max_records, 25),  # 降低单次请求量
            "format": "json",
            "sort": "DateDesc"  # 按日期降序
        }
        
        # 添加时间范围
        if start_date and end_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")
        
        # 添加速率限制控制
        retry_count = 0
        max_retries = 5  # 增加重试次数
        backoff_factor = 2.5  # 增加退避因子
        base_delay = 3  # 增加基础延迟
        
        while retry_count < max_retries:
            try:
                response = await self.http_client.get(
                    self.doc_api_url,
                    params=params,
                    timeout=30
                )
                
                # 检查429错误
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error("GDELT rate limit: Max retries exceeded, skipping")
                        break
                    # 指数退避 + 随机抖动，但限制最大等待时间
                    wait_time = min(base_delay * (backoff_factor ** retry_count) + (retry_count * 0.5), 30)
                    logger.warning(f"GDELT rate limit hit. Waiting {wait_time:.1f}s before retry ({retry_count}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                # 检查响应内容是否为空
                if not response.text or response.text.strip() == "":
                    logger.warning("GDELT returned empty response")
                    break
                
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"GDELT returned invalid JSON: {e}, content: {response.text[:200]}")
                    break
                
                # 解析文章列表
                articles = data.get("articles", [])
                
                for article in articles:
                    try:
                        # GDELT Doc API通常不直接返回完整内容，需要后续抓取
                        # 先使用标题和摘要作为内容
                        article_content = article.get("content", "") or article.get("snippet", "") or article.get("title", "")
                        
                        content = RawContent(
                            source="GDELT",
                            url=article.get("url", ""),
                            title=article.get("title", ""),
                            content=article_content,
                            published_at=self._parse_date(article.get("seendate")),
                            metadata={
                                "domain": article.get("domain", ""),
                                "language": article.get("language", ""),
                                "tone": article.get("tone", {}),
                                "source_country": article.get("sourcecountry", ""),
                                "gdelt_id": article.get("documentidentifier", ""),
                                "wordcount": article.get("wordcount", 0)
                            }
                        )
                        contents.append(content)
                    except Exception as e:
                        logger.warning(f"Error parsing GDELT article: {e}")
                        continue
                
                break  # 成功获取数据，退出循环
                
            except httpx.HTTPError as e:
                logger.error(f"GDELT HTTP error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = min(backoff_factor ** retry_count, 10)  # 限制最大等待时间
                    logger.warning(f"Retrying in {wait_time}s... ({retry_count}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded for GDELT API")
        
        return contents
    
    async def _fetch_article_content(self, url: str) -> str:
        """
        抓取文章完整内容
        注意：需要遵守robots.txt和网站条款
        """
        if not url:
            return ""
            
        try:
            # 添加延迟避免被封
            await asyncio.sleep(1)
            
            response = await self.http_client.get(
                url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            response.raise_for_status()
            
            # 简单的内容提取（实际项目中建议使用专门的库如newspaper3k）
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 提取正文内容
            content = soup.get_text()
            lines = (line.strip() for line in content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:5000]  # 限制长度
            
        except Exception as e:
            logger.debug(f"Failed to fetch content from {url}: {e}")
            return ""
    
    async def get_event_data(
        self,
        actors: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        获取事件数据（使用GDELT Events API）
        
        Args:
            actors: 行为体列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            事件数据列表
        """
        events_url = "https://api.gdeltproject.org/api/v2/events/events"
        
        # 构建查询
        actor_query = " OR ".join([f'actor:{actor}' for actor in actors])
        
        params = {
            "query": actor_query,
            "format": "json",
            "startdatetime": start_date.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end_date.strftime("%Y%m%d%H%M%S")
        }
        
        # 添加重试机制
        retry_count = 0
        max_retries = 3
        backoff_factor = 2
        
        while retry_count < max_retries:
            try:
                response = await self.http_client.get(events_url, params=params)
                
                if response.status_code == 429:
                    retry_count += 1
                    wait_time = backoff_factor ** retry_count
                    logger.warning(f"GDELT Events API rate limit. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                # 检查空响应
                if not response.text or response.text.strip() == "":
                    logger.warning("GDELT Events API returned empty response")
                    return []
                
                try:
                    data = response.json()
                    return data.get("data", [])
                except json.JSONDecodeError as e:
                    logger.error(f"GDELT Events API invalid JSON: {e}, content: {response.text[:200]}")
                    return []
                
            except Exception as e:
                logger.error(f"GDELT events API error: {type(e).__name__}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = backoff_factor ** retry_count
                    await asyncio.sleep(wait_time)
                    
        return []
    
    async def get_gkg_data(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        获取GKG（全球知识图）数据
        
        包含：实体、主题、情感、网络等
        """
        params = {
            "query": query,
            "format": "json",
            "startdatetime": start_date.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end_date.strftime("%Y%m%d%H%M%S")
        }
        
        # 添加重试机制
        retry_count = 0
        max_retries = 3
        backoff_factor = 2
        
        while retry_count < max_retries:
            try:
                response = await self.http_client.get(self.gkg_api_url, params=params)
                
                if response.status_code == 429:
                    retry_count += 1
                    wait_time = backoff_factor ** retry_count
                    logger.warning(f"GDELT GKG API rate limit. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                # 检查空响应
                if not response.text or response.text.strip() == "":
                    logger.warning("GDELT GKG API returned empty response")
                    return {}
                
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"GDELT GKG API invalid JSON: {e}, content: {response.text[:200]}")
                    return {}
                
            except Exception as e:
                logger.error(f"GDELT GKG API error: {type(e).__name__}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = backoff_factor ** retry_count
                    await asyncio.sleep(wait_time)
                    
        return {}
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析GDELT日期格式"""
        if not date_str:
            return None
        
        try:
            # GDELT格式: YYYYMMDDHHMMSS
            return datetime.strptime(date_str, "%Y%m%d%H%M%S")
        except ValueError:
            try:
                # 备选格式
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                return None
