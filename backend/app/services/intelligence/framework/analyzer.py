"""
内容分析器
使用LLM分析内容相关性、情感、关键事实
"""

import json
from typing import Dict, Any, List, Optional
from loguru import logger

from app.config import settings


class ContentAnalyzer:
    """
    内容分析器
    
    使用LLM分析：
    - 内容与查询的相关性
    - 情感倾向
    - 关键事实提取
    - 内容摘要
    """
    
    def __init__(self, model: str = None):
        self.model = model or settings.OPENAI_MODEL or "gpt-4-turbo-preview"
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化LLM客户端"""
        try:
            from openai import AsyncOpenAI
            
            if settings.OPENAI_API_KEY:
                self.client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
            else:
                logger.warning("OpenAI API key not configured")
        except ImportError:
            logger.error("OpenAI package not installed")
    
    async def analyze(self, content: str, query: str) -> Dict[str, Any]:
        """
        分析内容
        
        Args:
            content: 内容文本
            query: 原始查询
            
        Returns:
            分析结果
        """
        if not self.client:
            return {
                "relevance": 0.5,
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "sentiment": "neutral",
                "key_facts": []
            }
        
        # 截断长文本
        if len(content) > 6000:
            content = content[:6000] + "..."
        
        prompt = f"""
分析以下地缘政治相关内容：

原始查询：{query}

内容：
{content}

请分析并输出JSON格式：
{{
  "relevance": 与查询的相关性评分(0-1),
  "summary": "内容摘要(100字以内)",
  "sentiment": "情感倾向(positive/negative/neutral)",
  "key_facts": ["关键事实1", "关键事实2", "关键事实3"],
  "dimension_impacts": {{
    "economic": 经济维度影响(-1到1),
    "military": 军事维度影响(-1到1),
    "diplomatic": 外交维度影响(-1到1),
    "public_opinion": 舆论维度影响(-1到1)
  }}
}}

相关性评分标准：
- 0.9-1.0: 直接相关，核心内容
- 0.7-0.9: 高度相关，重要参考
- 0.5-0.7: 中度相关，有一定价值
- 0.3-0.5: 低度相关，参考价值有限
- 0.0-0.3: 几乎不相关
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的地缘政治内容分析专家。分析新闻内容的相关性、情感和关键信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content
            logger.info("=" * 50)
            logger.info("CONTENT ANALYZER LLM RAW RESPONSE:")
            logger.info(f"{result_text[:1000]}..." if len(result_text) > 1000 else result_text)
            logger.info("=" * 50)
            
            # 解析JSON
            result = self._safe_parse_json(result_text)
            
            if not result:
                logger.warning("Failed to parse content analysis response, using fallback")
                result = {
                    "relevance": 0.5,
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "sentiment": "neutral",
                    "key_facts": [],
                    "dimension_impacts": {
                        "economic": 0.0,
                        "military": 0.0,
                        "diplomatic": 0.0,
                        "public_opinion": 0.0
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return {
                "relevance": 0.5,
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "sentiment": "neutral",
                "key_facts": [],
                "dimension_impacts": {
                    "economic": 0.0,
                    "military": 0.0,
                    "diplomatic": 0.0,
                    "public_opinion": 0.0
                }
            }
    
    def _safe_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        安全解析JSON，处理各种格式问题
        """
        if not text:
            return None
        
        # 清理文本：替换中文引号为英文引号
        cleaned_text = text
        # 中文双引号 -> 英文双引号
        cleaned_text = cleaned_text.replace('"', '"').replace('"', '"')
        # 中文单引号 -> 英文单引号
        cleaned_text = cleaned_text.replace(''', "'").replace(''', "'")
        
        # 尝试直接解析
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON对象
        try:
            start = cleaned_text.find('{')
            end = cleaned_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = cleaned_text[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 尝试修复截断的JSON
        try:
            open_braces = cleaned_text.count('{')
            close_braces = cleaned_text.count('}')
            if open_braces > close_braces:
                cleaned_text += '}' * (open_braces - close_braces)
                return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试使用正则提取关键字段
        try:
            import re
            result = {}
            
            # 提取relevance
            relevance_match = re.search(r'"relevance"\s*:\s*([\d.]+)', cleaned_text)
            if relevance_match:
                result["relevance"] = float(relevance_match.group(1))
            
            # 提取summary
            summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', cleaned_text)
            if summary_match:
                result["summary"] = summary_match.group(1)
            
            # 提取sentiment
            sentiment_match = re.search(r'"sentiment"\s*:\s*"([^"]*)"', cleaned_text)
            if sentiment_match:
                result["sentiment"] = sentiment_match.group(1)
            
            if result:
                result.setdefault("relevance", 0.5)
                result.setdefault("summary", "")
                result.setdefault("sentiment", "neutral")
                result.setdefault("key_facts", [])
                result.setdefault("dimension_impacts", {
                    "economic": 0.0,
                    "military": 0.0,
                    "diplomatic": 0.0,
                    "public_opinion": 0.0
                })
                return result
        except Exception:
            pass
        
        logger.error(f"Failed to parse JSON after all attempts")
        return None
    
    async def summarize_multiple(
        self,
        contents: List[str],
        max_length: int = 500
    ) -> str:
        """
        对多个内容进行汇总摘要
        
        Args:
            contents: 内容列表
            max_length: 最大长度
            
        Returns:
            汇总摘要
        """
        if not self.client:
            return " ".join(contents)[:max_length]
        
        # 合并内容（限制总长度）
        combined = "\n\n---\n\n".join(contents[:5])  # 最多处理5个
        
        if len(combined) > 8000:
            combined = combined[:8000] + "..."
        
        prompt = f"""
对以下多条地缘政治新闻进行汇总摘要：

{combined}

请输出：
1. 总体摘要（{max_length}字以内）
2. 主要趋势和模式
3. 关键参与方

只输出汇总内容，不要其他格式。
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的新闻摘要专家。对多条新闻进行汇总分析。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return combined[:max_length]
    
    async def extract_key_events(
        self,
        content: str,
        timeframe: str = "recent"
    ) -> List[Dict[str, Any]]:
        """
        提取关键事件
        
        Args:
            content: 内容文本
            timeframe: 时间范围
            
        Returns:
            关键事件列表
        """
        if not self.client:
            return []
        
        if len(content) > 6000:
            content = content[:6000] + "..."
        
        prompt = f"""
从以下文本中提取关键地缘政治事件：

{content}

输出JSON数组格式：
[
  {{
    "event": "事件描述",
    "actor": "主要行为体",
    "action": "行动类型",
    "target": "目标（如果有）",
    "timeframe": "时间范围",
    "significance": "重要性(high/medium/low)"
  }}
]

只输出JSON，不要其他文字。
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个地缘政治事件提取专家。从文本中提取关键事件。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content
            logger.info("=" * 50)
            logger.info("EVENT EXTRACTOR LLM RAW RESPONSE:")
            logger.info(f"{result_text}")
            logger.info("=" * 50)
            
            # 解析JSON
            try:
                events = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
                if json_match:
                    events = json.loads(json_match.group())
                else:
                    events = []
            
            # Filter out None values from the list
            if isinstance(events, list):
                return [e for e in events if e is not None and isinstance(e, dict)]
            return []
            
        except Exception as e:
            logger.error(f"Event extraction error: {e}")
            return []
