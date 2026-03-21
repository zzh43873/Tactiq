"""
LLM实体提取器
使用大语言模型从文本中提取实体和关系
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from app.config import settings

# Constants for timeout and limits
LLM_TIMEOUT_SECONDS = 60  # Max time per LLM call (increased from 30)
MAX_ENTITIES_TO_ANALYZE = 10  # Limit entities to prevent long processing
MAX_RETRIES = 2  # Max retries for content filtering errors


class EntityExtractor:
    """
    实体提取器
    
    使用LLM从文本中提取
    - 实体（国家、组织、人物）
    - 实体类型和属性
    - 实体间关系
    - 事件和立场
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
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        if not self.client:
            logger.warning("LLM client not available, returning empty entities")
            return []
        
        if len(text) > 8000:
            text = text[:8000] + "..."
        
        prompt = self._build_extraction_prompt(text)
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Extracting entities (attempt {attempt + 1}/{MAX_RETRIES})...")
                
                # Use asyncio.wait_for to add timeout
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个专业的地缘政治实体提取专家。从文本中提取所有相关的国家、组织、武装团体、人物等实体。只输出JSON格式,不要包含任何政治敏感内容分析。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=2000
                    ),
                    timeout=LLM_TIMEOUT_SECONDS
                )
                
                content = response.choices[0].message.content
                logger.info("=" * 50)
                logger.info("LLM RAW RESPONSE:")
                logger.info(f"{content}")
                logger.info("=" * 50)

                # 解析JSON响应
                entities = self._parse_json_response(content)
                
                if entities:
                    logger.info(f"Successfully extracted {len(entities)} entities")
                    return entities
                
            except asyncio.TimeoutError:
                logger.error(f"Entity extraction timeout after {LLM_TIMEOUT_SECONDS}s (attempt {attempt + 1})")
                if attempt == MAX_RETRIES - 1:
                    # Return basic entities from text analysis instead of empty
                    logger.warning("Max retries reached due to timeout, returning basic entities")
                    return self._extract_basic_entities(text)
                continue
                
            except Exception as e:
                error_msg = str(e)
                # Handle content filtering errors
                if "data_inspection_failed" in error_msg or "inappropriate content" in error_msg:
                    logger.warning(f"Content filtering triggered (attempt {attempt + 1}): {e}")
                    if attempt == MAX_RETRIES - 1:
                        logger.error("Max retries reached for content filtering, returning empty")
                        return []
                    # Wait before retry
                    await asyncio.sleep(1)
                    continue
                
                logger.error(f"Entity extraction error: {e}")
                return []
        
        return []
    
    def _parse_json_response(self, content: str) -> Optional[List[Dict]]:
        """
        解析LLM返回的JSON响应
        """
        try:
            # 尝试直接解析
            entities = json.loads(content)
            if isinstance(entities, list):
                return [e for e in entities if e is not None and isinstance(e, dict)]
            elif isinstance(entities, dict):
                return [entities]
        except json.JSONDecodeError:
            pass
        
        # 尝试从代码块中提取
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                entities = json.loads(json_match.group(1))
                if isinstance(entities, list):
                    return [e for e in entities if e is not None and isinstance(e, dict)]
                elif isinstance(entities, dict):
                    return [entities]
            except json.JSONDecodeError:
                pass

        # 尝试从文本中提取JSON数组
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            try:
                entities = json.loads(json_match.group())
                if isinstance(entities, list):
                    return [e for e in entities if e is not None and isinstance(e, dict)]
            except json.JSONDecodeError:
                pass

        # 尝试从文本中提取JSON对象
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                entities = json.loads(json_match.group())
                if isinstance(entities, dict):
                    return [entities]
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Could not parse JSON from response: {content[:200]}...")
        return None
    
    async def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, List[List[str]]]:
        """
        提取实体间关系（使用6维度分类）
        
        Args:
            text: 输入文本
            entities: 已提取的实体列表
            
        Returns:
            关系网络（包含6维度分类的关系列表）
        """
        if not self.client:
            return {"allies": [], "adversaries": [], "complex": [], "key_relationships": []}
        
        entity_names = [e.get("name", "") for e in entities]
        
        prompt = f"""
分析以下文本中实体之间的关系：

文本：
{text[:3000]}

已识别的实体：
{', '.join(entity_names)}

请分析这些实体之间的关系，按以下6个维度分类，输出JSON格式：
{{
  "allies": [["实体A", "实体B"], ...],
  "adversaries": [["实体C", "实体D"], ...],
  "complex": [["实体E", "实体F"], ...],
  "key_relationships": [
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

关系定义：
- allies: 盟友关系，相互支持
- adversaries: 对抗关系，相互敌对
- complex: 复杂关系，既有合作又有竞争
- key_relationships: 详细的维度分类关系列表
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个国际关系分析专家。分析文本中实体之间的关系，并按6个维度进行分类。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON
            try:
                relationships = json.loads(content)
                # 确保 key_relationships 字段存在
                if "key_relationships" not in relationships:
                    relationships["key_relationships"] = []
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{{.*\}}', content, re.DOTALL)
                if json_match:
                    relationships = json.loads(json_match.group())
                    if "key_relationships" not in relationships:
                        relationships["key_relationships"] = []
                else:
                    relationships = {"allies": [], "adversaries": [], "complex": [], "key_relationships": []}
            
            return relationships
            
        except Exception as e:
            logger.error(f"Relationship extraction error: {e}")
            return {"allies": [], "adversaries": [], "complex": [], "key_relationships": []}
    
    async def analyze_entity_roles_batch(
        self,
        entities: List[Dict[str, Any]],
        event_description: str,
        context: str
    ) -> List[Dict[str, Any]]:
        """
        批量分析多个实体在事件中的角色（性能优化版本）
        
        Args:
            entities: 实体列表
            event_description: 事件描述
            context: 相关文本内容
            
        Returns:
            角色分析结果列表
        """
        if not self.client or not entities:
            return [self._default_role_analysis() for _ in entities]
        
        # Limit entities to prevent long processing
        if len(entities) > MAX_ENTITIES_TO_ANALYZE:
            logger.warning(f"Limiting entity analysis from {len(entities)} to {MAX_ENTITIES_TO_ANALYZE}")
            entities = entities[:MAX_ENTITIES_TO_ANALYZE]
        
        entity_names = [e.get("name", "") for e in entities if e.get("name")]
        
        prompt = f"""
分析以下实体在事件中的角色：

事件描述：
{event_description}

需要分析的实体：
{', '.join(entity_names)}

相关文本：
{context[:1500]}

请为每个实体输出分析结果，JSON格式：
{{
  "analyses": [
    {{
      "entity_name": "实体名称",
      "role": "角色类型(initiator/target/ally/proxy_actor/bystander等)",
      "relevance": 0.8,
      "current_actions": ["当前行动1"],
      "stated_position": "公开表态立场",
      "key_interests": ["核心利益1"]
    }}
  ]
}}
"""
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Batch analyzing {len(entity_names)} entities (attempt {attempt + 1})...")
                
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个地缘政治分析专家。批量分析多个实体在事件中的角色和立场。只输出JSON格式。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=2000
                    ),
                    timeout=LLM_TIMEOUT_SECONDS
                )
                
                content = response.choices[0].message.content
                
                # Parse response
                try:
                    result = json.loads(content)
                    analyses = result.get("analyses", [])
                    
                    # Create a map for quick lookup
                    analysis_map = {a.get("entity_name"): a for a in analyses}
                    
                    # Return analyses in the same order as input entities
                    results = []
                    for entity in entities:
                        name = entity.get("name", "")
                        if name in analysis_map:
                            analysis = analysis_map[name]
                            results.append({
                                "role": analysis.get("role", "unknown"),
                                "relevance_score": analysis.get("relevance", 0.5),
                                "current_actions": analysis.get("current_actions", []),
                                "stated_position": analysis.get("stated_position", ""),
                                "key_interests": analysis.get("key_interests", [])
                            })
                        else:
                            results.append(self._default_role_analysis())
                    
                    logger.info(f"Successfully analyzed {len(results)} entities in batch")
                    return results
                    
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse batch analysis response: {content[:200]}...")
                    if attempt == MAX_RETRIES - 1:
                        return [self._default_role_analysis() for _ in entities]
                    
            except asyncio.TimeoutError:
                logger.error(f"Batch analysis timeout after {LLM_TIMEOUT_SECONDS}s (attempt {attempt + 1})")
                if attempt == MAX_RETRIES - 1:
                    return [self._default_role_analysis() for _ in entities]
                    
            except Exception as e:
                error_msg = str(e)
                if "data_inspection_failed" in error_msg or "inappropriate content" in error_msg:
                    logger.warning(f"Content filtering in batch analysis (attempt {attempt + 1})")
                    if attempt == MAX_RETRIES - 1:
                        return [self._default_role_analysis() for _ in entities]
                    await asyncio.sleep(1)
                    continue
                    
                logger.error(f"Batch analysis error: {e}")
                return [self._default_role_analysis() for _ in entities]
        
        return [self._default_role_analysis() for _ in entities]
    
    def _default_role_analysis(self) -> Dict[str, Any]:
        """返回默认的角色分析结果"""
        return {
            "role": "unknown",
            "relevance_score": 0.5,
            "current_actions": [],
            "stated_position": "",
            "key_interests": []
        }
    
    def _extract_basic_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取基础实体（不使用LLM，用于超时降级）
        
        使用简单的关键词匹配提取已知的国家和组织
        """
        import re
        
        # 已知实体数据库
        known_entities = {
            "countries": ["美国", "中国", "俄罗斯", "伊朗", "以色列", "沙特", "叙利亚", "黎巴嫩", "也门", "伊拉克", "阿富汗", "巴基斯坦", "印度", "朝鲜", "韩国", "日本", "英国", "法国", "德国", "土耳其", "埃及", "乌克兰", "台湾"],
            "organizations": ["联合国", "北约", "欧盟", "阿拉伯联盟", "真主党", "哈马斯", "胡塞武装", "伊斯兰国", "基地组织"],
        }
        
        entities = []
        entity_id = 0
        
        # 提取国家
        for country in known_entities["countries"]:
            if country in text:
                entities.append({
                    "id": f"entity_{entity_id}",
                    "name": country,
                    "type": "country",
                    "mentions": text.count(country),
                    "context": self._extract_context(text, country)
                })
                entity_id += 1
        
        # 提取组织
        for org in known_entities["organizations"]:
            if org in text:
                entities.append({
                    "id": f"entity_{entity_id}",
                    "name": org,
                    "type": "organization",
                    "mentions": text.count(org),
                    "context": self._extract_context(text, org)
                })
                entity_id += 1
        
        logger.info(f"Basic extraction found {len(entities)} entities")
        return entities
    
    def _extract_context(self, text: str, keyword: str, window: int = 50) -> str:
        """提取关键词周围的上下文"""
        import re
        pattern = re.compile(re.escape(keyword))
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            return text[start:end].replace("\n", " ")
        return ""
    
    async def analyze_entity_role(
        self,
        entity_name: str,
        event_description: str,
        context: str
    ) -> Dict[str, Any]:
        """
        分析单个实体在事件中的角色（已弃用，请使用 analyze_entity_roles_batch）
        
        保留此方法用于向后兼容，但内部使用批量处理
        """
        results = await self.analyze_entity_roles_batch(
            [{"name": entity_name}],
            event_description,
            context
        )
        return results[0] if results else self._default_role_analysis()
    
    def _build_extraction_prompt(self, text: str) -> str:
        """构建实体提取提示词"""
        return f"""
从以下地缘政治相关文本中提取所有实体：

文本：
{text}

请提取以下类型的实体：
1. 主权国家（如：美国、中国、俄罗斯）
2. 国际组织（如：联合国、北约、欧盟）
3. 非国家武装组织（如：哈马斯、真主党）
4. 地区势力
5. 重要政治人物

对于每个实体，输出以下信息：
- name: 实体名称（中文）
- name_en: 英文名称（如果有）
- entity_type: 实体类型（country/organization/non_state_armed/regional_power/person）
- attributes: 关键属性（如经济实力、军事实力等，0-1评分）

输出JSON数组格式：
[
  {{
    "name": "实体名称",
    "name_en": "English Name",
    "entity_type": "country",
    "attributes": {{
      "economic_power": 0.8,
      "military_power": 0.9
    }}
  }}
]

只输出JSON，不要其他文字。
"""
