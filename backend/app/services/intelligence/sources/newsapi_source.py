"""
NewsAPI数据源
国际新闻聚合服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from loguru import logger

from app.services.intelligence.framework.crawler import DataSource, RawContent
from app.config import settings


class NewsAPISource(DataSource):
    """
    NewsAPI数据源
    
    提供来自全球70,000+新闻源的新闻
    
    特点：
    - 实时新闻
    - 多语言支持
    - 丰富的元数据
    - 需要API key
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("NewsAPI", config)
        self.api_key = (config or {}).get("api_key") or settings.NEWSAPI_KEY
        self.base_url = "https://newsapi.org/v2"
    
    def is_available(self) -> bool:
        """检查是否有API key"""
        if not self.api_key or self.api_key == "your-newsapi-key":
            logger.info("NewsAPI key not configured, skipping NewsAPI source")
            return False
        return True
    
    async def search(
        self,
        query: str,
        **kwargs
    ) -> List[RawContent]:
        """
        搜索新闻
        
        Args:
            query: 搜索关键词
            from_date: 开始日期 (YYYY-MM-DD)
            to_date: 结束日期 (YYYY-MM-DD)
            language: 语言代码 (en, zh, ar, etc.)
            sort_by: 排序方式 (relevancy, popularity, publishedAt)
            page_size: 每页数量 (max 100)
            
        Returns:
            原始内容列表
        """
        if not self.api_key:
            logger.warning("NewsAPI key not configured")
            return []
        
        # 构建参数
        params = {
            "q": query,
            "apiKey": self.api_key,
            "pageSize": kwargs.get('page_size', 50),
            "sortBy": kwargs.get('sort_by', 'relevancy')
        }
        
        # 添加时间范围
        if 'from_date' in kwargs:
            params["from"] = kwargs['from_date']
        if 'to_date' in kwargs:
            params["to"] = kwargs['to_date']
        
        # 添加语言过滤
        if 'language' in kwargs:
            params["language"] = kwargs['language']
        
        # 添加域名过滤
        if 'domains' in kwargs:
            params["domains"] = kwargs['domains']
        
        try:
            response = await self.http_client.get(
                f"{self.base_url}/everything",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "ok":
                logger.error(f"NewsAPI error: {data.get('message')}")
                return []
            
            articles = data.get("articles", [])
            
            contents = []
            for article in articles:
                try:
                    content = RawContent(
                        source="NewsAPI",
                        url=article.get("url", ""),
                        title=article.get("title", ""),
                        content=article.get("content", "") or article.get("description", ""),
                        published_at=self._parse_date(article.get("publishedAt")),
                        metadata={
                            "source_name": article.get("source", {}).get("name", ""),
                            "author": article.get("author", ""),
                            "url_to_image": article.get("urlToImage", ""),
                            "language": kwargs.get('language', 'unknown')
                        }
                    )
                    contents.append(content)
                except Exception as e:
                    logger.warning(f"Error parsing NewsAPI article: {e}")
                    continue
            
            logger.info(f"NewsAPI found {len(contents)} articles for '{query}'")
            return contents
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("NewsAPI authentication failed - check API key")
            elif e.response.status_code == 429:
                logger.error("NewsAPI rate limit exceeded")
            else:
                logger.error(f"NewsAPI HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"NewsAPI search error: {e}")
            return []
    
    async def get_top_headlines(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 20
    ) -> List[RawContent]:
        """
        获取头条新闻
        
        Args:
            country: 国家代码 (us, cn, gb, etc.)
            category: 类别 (business, entertainment, general, health, science, sports, technology)
            query: 搜索关键词
            page_size: 每页数量
        """
        if not self.api_key:
            return []
        
        params = {
            "apiKey": self.api_key,
            "pageSize": page_size
        }
        
        if country:
            params["country"] = country
        if category:
            params["category"] = category
        if query:
            params["q"] = query
        
        try:
            response = await self.http_client.get(
                f"{self.base_url}/top-headlines",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            contents = []
            for article in articles:
                try:
                    content = RawContent(
                        source="NewsAPI-Headlines",
                        url=article.get("url", ""),
                        title=article.get("title", ""),
                        content=article.get("content", "") or article.get("description", ""),
                        published_at=self._parse_date(article.get("publishedAt")),
                        metadata={
                            "source_name": article.get("source", {}).get("name", ""),
                            "category": category,
                            "country": country
                        }
                    )
                    contents.append(content)
                except Exception as e:
                    logger.warning(f"Error parsing headline: {e}")
                    continue
            
            return contents
            
        except Exception as e:
            logger.error(f"NewsAPI headlines error: {e}")
            return []
    
    async def get_sources(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取可用的新闻源列表"""
        if not self.api_key:
            return []
        
        params = {"apiKey": self.api_key}
        
        if category:
            params["category"] = category
        if language:
            params["language"] = language
        if country:
            params["country"] = country
        
        try:
            response = await self.http_client.get(
                f"{self.base_url}/sources",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("sources", [])
            
        except Exception as e:
            logger.error(f"NewsAPI sources error: {e}")
            return []
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析ISO格式日期"""
        if not date_str:
            return None
        
        try:
            # NewsAPI使用ISO 8601格式
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
