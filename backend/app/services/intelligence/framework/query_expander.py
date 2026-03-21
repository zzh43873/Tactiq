"""
智能查询扩展器
将用户推演命题扩展为多个互补的搜索查询
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger

from app.config import settings


@dataclass
class ExpandedQuery:
    """扩展的查询"""
    query: str  # 中文查询（用于展示）
    query_en: str  # 英文查询（用于GDELT搜索）
    query_type: str  # current_context, historical, impact, stakeholder
    rationale: str  # 为什么这个查询重要
    priority: int  # 优先级 1-5


@dataclass
class PreIdentifiedEntity:
    """预识别的实体"""
    name: str
    entity_type: str  # country, organization, non_state_actor, international_org
    role: str  # initiator, target, ally, adversary, mediator, stakeholder
    relevance: float
    rationale: str
    key_interests: List[str]
    name_en: Optional[str] = None  # 英文名称，用于GDELT搜索


@dataclass
class QueryExpansionResult:
    """查询扩展结果"""
    original_query: str
    expanded_queries: List[ExpandedQuery]
    pre_identified_entities: List[PreIdentifiedEntity]
    relationships: List[Dict[str, Any]]


class QueryExpander:
    """
    智能查询扩展器
    
    功能：
    1. 将单一推演命题扩展为多个搜索查询
    2. 预识别可能涉及的所有实体
    3. 分析实体间关系
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
    
    async def expand_query(self, original_query: str) -> QueryExpansionResult:
        """
        扩展用户查询
        
        Args:
            original_query: 原始推演命题，如"美国出兵伊朗"
            
        Returns:
            QueryExpansionResult: 扩展结果
        """
        if not self.client:
            # 如果没有LLM客户端，返回基础扩展
            return self._fallback_expansion(original_query)
        
        # Step 1: 查询扩展
        expanded_queries = await self._generate_expanded_queries(original_query)
        
        # Step 2: 实体预识别
        entities, relationships = await self._pre_identify_entities(original_query)
        
        return QueryExpansionResult(
            original_query=original_query,
            expanded_queries=expanded_queries,
            pre_identified_entities=entities,
            relationships=relationships
        )
    
    async def _generate_expanded_queries(self, original_query: str) -> List[ExpandedQuery]:
        """生成扩展查询"""
        prompt = f"""
你是一位地缘政治情报分析专家。用户想要进行一个地缘政治推演，输入的命题是：

"{original_query}"

这个命题可能是一个假设性场景（尚未发生），也可能是基于当前局势的预测。

你的任务是：将这个命题扩展为4个不同维度的搜索查询，以便收集全面的背景情报。

扩展维度：
1. **当前背景** (current_context): 当前相关的局势和关系
2. **历史类比** (historical): 历史上类似的事件和后果
3. **影响推演** (impact): 如果发生会产生什么影响
4. **相关方分析** (stakeholders): 涉及的其他国家和组织

输出JSON格式：
{{
  "expanded_queries": [
    {{
      "query": "具体的搜索查询语句（中文）",
      "query_en": "对应的英文搜索查询语句（用于国际数据库搜索）",
      "query_type": "current_context|historical|impact|stakeholder",
      "rationale": "为什么这个查询重要（中文）",
      "priority": 1-5
    }}
  ]
}}

要求：
- 每个查询应该同时提供中文和英文版本
- 中文查询用于展示给用户，英文查询用于GDELT等国际数据库搜索
- 英文查询应该使用标准的地缘政治术语和国际通用表达
- 查询应该覆盖不同角度，避免重复
- 优先级1最高，5最低
- 只输出JSON，不要其他文字
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是地缘政治情报分析专家，擅长将推演命题扩展为多维度的搜索查询。"
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
            logger.info("QUERY EXPANSION LLM RESPONSE:")
            logger.info(result_text)
            logger.info("=" * 50)
            
            # 解析JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise
            
            queries = []
            for q in result.get("expanded_queries", []):
                queries.append(ExpandedQuery(
                    query=q["query"],
                    query_en=q.get("query_en", q["query"]),  # 如果没有英文查询，使用中文查询
                    query_type=q["query_type"],
                    rationale=q["rationale"],
                    priority=q["priority"]
                ))
            
            return queries
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return self._fallback_expanded_queries(original_query)
    
    async def _pre_identify_entities(self, original_query: str) -> tuple[List[PreIdentifiedEntity], List[Dict]]:
        """预识别实体"""
        prompt = f"""
你是一位地缘政治实体识别专家。用户想要推演以下场景：

"{original_query}"

请识别如果这一事件发生，全球范围内所有可能涉及的相关实体。

考虑维度：
1. **直接参与方**: 事件的主要行动者和目标
2. **地区邻国**: 地理位置上受影响的国家
3. **大国利益相关方**: 有战略利益的大国
4. **国际组织**: 可能介入或受影响的国际机构
5. **经济相关方**: 在经济上受影响的国家或组织（能源、贸易等）
6. **军事同盟**: 相关的军事同盟和防务关系
7. **非国家行为体**: 武装组织、恐怖组织等

输出JSON格式：
{{
  "entities": [
    {{
      "name": "实体名称（中文）",
      "entity_type": "country|organization|non_state_actor|international_org",
      "role": "initiator|target|ally|adversary|mediator|economic_stakeholder|military_actor|regional_actor",
      "relevance": 0.0-1.0,
      "rationale": "为什么这个实体相关（中文）",
      "key_interests": ["利益1", "利益2"]
    }}
  ],
  "relationships": [
    {{
      "entity_a": "实体A名称",
      "entity_b": "实体B名称",
      "relationship": "关系类型名称",
      "dimension": "political|security|economic|social|ideological|geostrategic",
      "tension_level": 0.0-1.0,
      "description": "关系描述"
    }}
  ]
}}

关系维度说明：
- **political**: 政治与外交关系（外交承认、政治同盟、外交冲突等）
- **security**: 安全与军事合作（军事同盟、防务合作、军事冲突、军售等）
- **economic**: 经济与贸易联系（贸易伙伴、经济制裁、能源合作、投资关系等）
- **social**: 社会文化纽带（文化联系、人员往来、侨民关系等）
- **ideological**: 意识形态与价值观（政治体制相似性、价值观同盟等）
- **geostrategic**: 地缘战略互动（地缘竞争、战略缓冲区、航道控制等）

要求：
- 尽可能全面，不要遗漏重要实体
- 每个实体都要有明确的角色和相关性评分
- 识别实体间的重要关系，每个关系必须指定一个维度
- 同一对实体可以有多个不同维度的关系
- 只输出JSON，不要其他文字
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是地缘政治实体识别专家，擅长识别复杂国际局势中的所有相关方。只输出有效的JSON格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=8000  # 增加token限制以避免截断
            )
            
            result_text = response.choices[0].message.content
            logger.info("=" * 50)
            logger.info("ENTITY PRE-IDENTIFICATION LLM RESPONSE:")
            logger.info(result_text)  # Log full response for debugging
            logger.info("=" * 50)
            
            # 解析JSON，处理可能的截断
            result = self._safe_parse_json(result_text)
            
            if not result:
                logger.warning("Failed to parse entity pre-identification response")
                return [], []
            
            entities = []
            for e in result.get("entities", []):
                try:
                    entities.append(PreIdentifiedEntity(
                        name=e.get("name", ""),
                        entity_type=e.get("entity_type", "unknown"),
                        role=e.get("role", "unknown"),
                        relevance=e.get("relevance", 0.5),
                        rationale=e.get("rationale", ""),
                        key_interests=e.get("key_interests", []),
                        name_en=e.get("name_en")
                    ))
                except Exception as entity_error:
                    logger.warning(f"Failed to parse entity: {e}, error: {entity_error}")
                    continue
            
            relationships = result.get("relationships", [])
            
            logger.info(f"Successfully pre-identified {len(entities)} entities and {len(relationships)} relationships")
            return entities, relationships
            
        except Exception as e:
            logger.error(f"Entity pre-identification failed: {e}")
            return [], []
    
    def _normalize_json_text(self, text: str) -> str:
        """
        规范化JSON文本，处理中文引号等常见问题
        """
        # 替换中文引号为英文引号
        replacements = [
            ('"', '"'),  # 左双引号
            ('"', '"'),  # 右双引号
            (''', "'"),  # 左单引号
            (''', "'"),  # 右单引号
            ('「', '"'),  # 日式左引号
            ('」', '"'),  # 日式右引号
            ('『', "'"),  # 日式左单引号
            ('』', "'"),  # 日式右单引号
        ]
        
        for old, new in replacements:
            text = text.replace(old, new)
        
        return text
    
    def _safe_parse_json(self, text: str) -> Optional[Dict]:
        """
        安全解析JSON，处理截断、中文引号或不完整的情况
        """
        # 首先规范化文本（处理中文引号等）
        normalized_text = self._normalize_json_text(text)
        
        # 尝试直接解析
        try:
            return json.loads(normalized_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON对象
        try:
            # 查找最外层的大括号
            start = normalized_text.find('{')
            end = normalized_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = normalized_text[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 尝试修复截断的JSON（如果缺少闭合括号）
        try:
            # 计算开闭括号数量
            open_braces = normalized_text.count('{')
            close_braces = normalized_text.count('}')
            open_brackets = normalized_text.count('[')
            close_brackets = normalized_text.count(']')
            
            fixed_text = normalized_text
            if open_braces > close_braces:
                # 添加缺少的闭合大括号
                fixed_text += '}' * (open_braces - close_braces)
            if open_brackets > close_brackets:
                # 添加缺少的闭合中括号
                fixed_text += ']' * (open_brackets - close_brackets)
            
            return json.loads(fixed_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取entities部分（即使relationships被截断）
        try:
            import re
            # 匹配entities数组（支持多种引号格式）
            entities_match = re.search(r'["\']entities["\']\s*:\s*(\[.*?\])(?:\s*[,}\]])', normalized_text, re.DOTALL)
            if entities_match:
                entities_str = entities_match.group(1)
                entities = json.loads(entities_str)
                return {"entities": entities, "relationships": []}
        except Exception:
            pass
        
        # 最后尝试：提取任何可能的JSON对象
        try:
            import re
            # 查找所有可能的JSON对象
            json_pattern = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)
            matches = json_pattern.findall(normalized_text)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if 'entities' in parsed or 'relationships' in parsed:
                        return parsed
                except:
                    continue
        except Exception:
            pass
        
        logger.error(f"Failed to parse JSON after all attempts. Raw text preview: {text[:500]}...")
        return None
    
    def _fallback_expansion(self, original_query: str) -> QueryExpansionResult:
        """备用扩展（无LLM时）"""
        expanded_queries = self._fallback_expanded_queries(original_query)
        return QueryExpansionResult(
            original_query=original_query,
            expanded_queries=expanded_queries,
            pre_identified_entities=[],
            relationships=[]
        )
    
    def _fallback_expanded_queries(self, original_query: str) -> List[ExpandedQuery]:
        """备用扩展查询"""
        return [
            ExpandedQuery(
                query=f"当前{original_query}局势",
                query_en=f"current situation {original_query}",
                query_type="current_context",
                rationale="了解当前相关背景",
                priority=1
            ),
            ExpandedQuery(
                query=f"{original_query}历史案例",
                query_en=f"historical cases {original_query}",
                query_type="historical",
                rationale="参考历史类似事件",
                priority=2
            ),
            ExpandedQuery(
                query=f"{original_query}国际影响",
                query_en=f"international impact {original_query}",
                query_type="impact",
                rationale="了解可能的后果",
                priority=2
            ),
            ExpandedQuery(
                query=f"{original_query}相关国家",
                query_en=f"related countries {original_query}",
                query_type="stakeholder",
                rationale="识别涉及的国家",
                priority=3
            )
        ]
