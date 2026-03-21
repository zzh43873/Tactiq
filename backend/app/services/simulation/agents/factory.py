"""
Agent工厂模块
根据情报报告动态创建和初始化Agent
"""

from typing import Dict, List, Optional, Type
from loguru import logger
from datetime import datetime

from app.services.intelligence.collector import (
    IntelligenceReport,
    EntityIdentification
)
from app.services.simulation.agents.base import EntityAgent, Perception, Decision, Action


class GenericEntityAgent(EntityAgent):
    """
    通用实体Agent实现
    用于没有特定实现的实体
    """

    def perceive(self, event: Dict, context: Dict) -> Perception:
        """感知阶段"""
        return Perception(
            event_understanding=event.get("description", event.get("type", "Unknown event")),
            threat_assessment=self._calculate_threat(event),
            opportunity_assessment=self._calculate_opportunity(event),
            affected_interests=self._assess_relevance_list(event)
        )

    def decide(self, perception: Perception,
               available_actions: List[Action],
               other_agents_states: Dict) -> Decision:
        """决策阶段"""
        # 选择最符合自身利益的动作
        best_action = None
        best_score = -float('inf')

        for action in available_actions:
            score = self._evaluate_action(action, perception, other_agents_states)
            if score > best_score:
                best_score = score
                best_action = action

        return Decision(
            action=best_action or available_actions[0] if available_actions else None,
            confidence=min(best_score, 1.0),
            reasoning=f"Based on {self.profile.get('name', 'entity')} interests and current situation",
            alternatives=available_actions[:3]
        )

    def act(self, decision: Decision) -> Action:
        """行动阶段"""
        if decision.action:
            return Action(
                type=decision.action.type,
                target=decision.action.target,
                content=decision.action.content,
                intensity=decision.action.intensity,
                expected_outcome=decision.action.expected_outcome
            )
        return Action(
            type="wait",
            target=None,
            content="维持现状，观察局势发展",
            intensity=0.1,
            expected_outcome="保持灵活性"
        )

    def _calculate_threat(self, event: Dict) -> float:
        """计算威胁程度 (-1 to 1)"""
        event_type = event.get("type", "")
        if any(word in event_type.lower() for word in ["attack", "conflict", "war", "制裁", "军事"]):
            return 0.7
        return 0.0

    def _calculate_opportunity(self, event: Dict) -> float:
        """计算机会程度 (-1 to 1)"""
        event_type = event.get("type", "")
        if any(word in event_type.lower() for word in ["cooperation", "trade", "合作", "贸易"]):
            return 0.5
        return 0.0

    def _assess_relevance_list(self, event: Dict) -> List[str]:
        """评估与核心利益的相关性，返回相关利益列表"""
        interests = self.profile.get("core_interests", [])
        # 返回前3个核心利益作为受影响利益
        return interests[:3] if interests else ["general interest"]

    def _evaluate_action(self, action: Action, perception: Perception,
                        other_agents_states: Dict) -> float:
        """评估动作的效用"""
        base_score = 0.5
        # 根据动作类型调整分数
        if action.type == "diplomatic":
            base_score += 0.1
        elif action.type == "military":
            base_score += 0.2 if perception.urgency > 0.7 else -0.1
        return min(max(base_score, 0.0), 1.0)


# Agent模板库
# 每个模板包含实体的基础画像、决策模式、核心利益等
AGENT_TEMPLATES = {
    # === 主权国家 ===
    "usa": {
        "name": "美国",
        "name_en": "United States",
        "type": "sovereign_state",
        "attributes": {
            "economic_power": 0.95,
            "military_power": 0.95,
            "diplomatic_influence": 0.9,
            "domestic_stability": 0.7,
            "strategic_patience": 0.6,
            "risk_tolerance": 0.5
        },
        "core_interests": [
            "全球霸权地位",
            "盟友体系稳定",
            "经济主导地位",
            "技术领先优势"
        ],
        "decision_patterns": [
            "优先考虑联盟协调",
            "经济制裁优先于军事干预",
            "避免直接大国冲突"
        ]
    },
    
    "china": {
        "name": "中国",
        "name_en": "China",
        "type": "sovereign_state",
        "attributes": {
            "economic_power": 0.85,
            "military_power": 0.75,
            "diplomatic_influence": 0.8,
            "domestic_stability": 0.8,
            "strategic_patience": 0.9,
            "risk_tolerance": 0.4
        },
        "core_interests": [
            "领土完整",
            "经济发展",
            "政权稳定",
            "区域影响力"
        ],
        "decision_patterns": [
            "长期战略规划",
            "底线思维",
            "发展优先",
            "不首先使用武力"
        ]
    },
    
    "russia": {
        "name": "俄罗斯",
        "name_en": "Russia",
        "type": "sovereign_state",
        "attributes": {
            "economic_power": 0.5,
            "military_power": 0.8,
            "diplomatic_influence": 0.6,
            "domestic_stability": 0.6,
            "strategic_patience": 0.5,
            "risk_tolerance": 0.7
        },
        "core_interests": [
            "势力范围",
            "政权生存",
            "能源影响力",
            "军事威慑"
        ],
        "decision_patterns": [
            "地缘博弈优先",
            "风险承受度高",
            "反制果断",
            "利用不对称优势"
        ]
    },
    
    "iran": {
        "name": "伊朗",
        "name_en": "Iran",
        "type": "sovereign_state",
        "attributes": {
            "economic_power": 0.4,
            "military_power": 0.6,
            "diplomatic_influence": 0.5,
            "domestic_stability": 0.5,
            "strategic_patience": 0.6,
            "risk_tolerance": 0.6
        },
        "core_interests": [
            "政权生存",
            "地区影响力",
            "核计划",
            "抵抗轴心"
        ],
        "decision_patterns": [
            "代理人策略",
            "非对称对抗",
            "战略耐心与机会主义并存",
            "利用地区矛盾"
        ]
    },
    
    "israel": {
        "name": "以色列",
        "name_en": "Israel",
        "type": "sovereign_state",
        "attributes": {
            "economic_power": 0.7,
            "military_power": 0.85,
            "diplomatic_influence": 0.7,
            "domestic_stability": 0.6,
            "strategic_patience": 0.4,
            "risk_tolerance": 0.6
        },
        "core_interests": [
            "国家安全",
            "犹太人国家地位",
            "地区优势",
            "美国支持"
        ],
        "decision_patterns": [
            "先发制人",
            "情报驱动",
            "过度报复威慑",
            "依赖美国支持"
        ]
    },
    
    "saudi_arabia": {
        "name": "沙特阿拉伯",
        "name_en": "Saudi Arabia",
        "type": "sovereign_state",
        "attributes": {
            "economic_power": 0.7,
            "military_power": 0.5,
            "diplomatic_influence": 0.7,
            "domestic_stability": 0.6,
            "strategic_patience": 0.5,
            "risk_tolerance": 0.4
        },
        "core_interests": [
            "王室统治",
            "石油霸权",
            "逊尼派领袖",
            "遏制伊朗"
        ],
        "decision_patterns": [
            "经济杠杆优先",
            "宗教影响力",
            "依赖美国保护",
            "谨慎冒险"
        ]
    },
    
    # === 非国家武装组织 ===
    "hamas": {
        "name": "哈马斯",
        "name_en": "Hamas",
        "type": "non_state_armed",
        "attributes": {
            "military_strength": 0.3,
            "popular_support": 0.6,
            "external_support": 0.5,
            "economic_resources": 0.2,
            "international_legitimacy": 0.1
        },
        "core_interests": [
            "组织生存",
            "巴勒斯坦建国",
            "对抗以色列",
            "国际承认"
        ],
        "decision_patterns": [
            "非对称战术",
            "舆论战优先",
            "利用平民伤亡",
            "寻求地区支持"
        ]
    },
    
    "hezbollah": {
        "name": "黎巴嫩真主党",
        "name_en": "Hezbollah",
        "type": "non_state_armed",
        "attributes": {
            "military_strength": 0.5,
            "popular_support": 0.5,
            "external_support": 0.7,
            "economic_resources": 0.3,
            "international_legitimacy": 0.2
        },
        "core_interests": [
            "组织生存",
            "黎巴嫩影响力",
            "支持巴勒斯坦",
            "伊朗代理人"
        ],
        "decision_patterns": [
            "伊朗协调行动",
            "火箭弹威慑",
            "地面游击战",
            "政治军事双轨"
        ]
    },
    
    "houthis": {
        "name": "胡塞武装",
        "name_en": "Houthis",
        "type": "non_state_armed",
        "attributes": {
            "military_strength": 0.3,
            "popular_support": 0.4,
            "external_support": 0.5,
            "economic_resources": 0.2,
            "international_legitimacy": 0.1
        },
        "core_interests": [
            "也门统治",
            "对抗沙特",
            "支持巴勒斯坦",
            "红海控制"
        ],
        "decision_patterns": [
            "非对称作战",
            "袭击航运",
            "伊朗支持",
            "持久消耗"
        ]
    }
}


class AgentFactory:
    """
    Agent工厂
    根据情报报告动态创建和初始化Agent
    """
    
    def __init__(self):
        self.templates = AGENT_TEMPLATES

    def create_agents(
        self, 
       intelligence: IntelligenceReport
    ) -> List[EntityAgent]:
        """
        根据情报报告动态创建Agent列表
        
        Args:
           intelligence: 包含已识别实体和态势的情报报告
            
        Returns:
            初始化的Agent列表
        """
        agents = []
        
        for entity in intelligence.identified_entities:
            # 只处理高相关度的实体
            if entity.relevance_score < 0.5:
                logger.debug(f"Skipping low-relevance entity: {entity.name}")
                continue
            
            # Step 1: 从模板库加载基础画像
            template = self._load_template(entity.name)
            
            if not template:
                # 如果没有预定义模板，尝试用英文名称匹配
                template = self._load_template(entity.name_en)
            
            if not template:
                # 如果还是没有，使用通用模板+LLM生成
                logger.warning(f"No template found for {entity.name}, using generic template")
                template = self._create_generic_template(entity)
            
            # Step 2: 注入当前态势信息
            agent_profile = self._inject_situation(template, entity, intelligence)
            
            # Step 3: 初始化记忆（注入历史互动、当前承诺）
            agent_profile = self._initialize_memory(agent_profile, entity, intelligence)
            
            # Step 4: 创建Agent实例
            agent = self._instantiate_agent(agent_profile)
            agents.append(agent)
            
            logger.info(f"Created agent for {entity.name} (role: {entity.role})")

        return agents

    def _load_template(self, entity_name: Optional[str]) -> Optional[Dict]:
        """从模板库加载"""
        if not entity_name:
            return None

        # 标准化名称用于匹配
        normalized_name = entity_name.lower().replace(" ", "_").replace("-", "_")

        return self.templates.get(normalized_name)

    def _create_generic_template(self, entity: EntityIdentification) -> Dict:
        """
        为未知实体创建通用模板
        TODO: 实际实现时使用LLM生成
        """
        base_template = {
            "name": entity.name,
            "name_en": entity.name_en or entity.name,
            "type": entity.entity_type,
            "attributes": {
                "economic_power": 0.5,
                "military_power": 0.5,
                "diplomatic_influence": 0.5,
                "domestic_stability": 0.5,
                "strategic_patience": 0.5,
                "risk_tolerance": 0.5
            },
            "core_interests": entity.key_interests or ["生存", "安全"],
            "decision_patterns": ["理性决策", "利益优先"]
        }

        # 根据实体类型调整
        if entity.entity_type == "non_state_armed":
            base_template["attributes"]["military_strength"] = 0.3
            base_template["attributes"]["popular_support"] = 0.4

        return base_template

    def _inject_situation(
        self,
        template: Dict,
        entity: EntityIdentification,
        intelligence: IntelligenceReport
    ) -> Dict:
        """
        注入当前态势信息到Agent画像

        包括：
        - 当前行动
        - 表态立场
        - 角色定位
        """
        profile = template.copy()

        # 注入当前态势
        profile["current_situation"] = {
            "role": entity.role,
            "current_actions": entity.current_actions,
            "stated_position": entity.stated_position,
            "relevance": entity.relevance_score
        }

        # 注入关系网络（从情报报告中提取）
        relationships = self._extract_relationships(entity.name, intelligence)
        profile["relationships"] = relationships

        return profile

    def _extract_relationships(
        self,
        entity_name: str,
        intelligence: IntelligenceReport
    ) -> Dict:
        """从情报中提取关系网络"""
        allies = []
        adversaries = []
        complex_relations = []

        dynamics = intelligence.relationship_dynamics

        # Ensure dynamics is not None
        if not dynamics:
            return {
                "allies": [],
                "adversaries": [],
                "complex": []
            }

        # 查找盟友关系
        for coop_pair in dynamics.cooperation:
            if entity_name in coop_pair:
                partner = coop_pair[0] if coop_pair[1] == entity_name else coop_pair[1]
                allies.append(partner)

        # 查找对手关系
        for conflict_pair in dynamics.active_conflicts + dynamics.tensions:
            if entity_name in conflict_pair:
                opponent = conflict_pair[0] if conflict_pair[1] == entity_name else conflict_pair[1]
                adversaries.append(opponent)

        return {
            "allies": allies,
            "adversaries": adversaries,
            "complex": complex_relations
        }

    def _initialize_memory(
        self,
        profile: Dict,
        entity: EntityIdentification,
        intelligence: IntelligenceReport
    ) -> Dict:
        """
        初始化Agent记忆

        注入：
        - 当前承诺
        - 历史互动（简化版，TODO: 扩展）
        - 信任评分
        """
        memory = {
            "short_term": [],
            "commitments": [],
            "trust_scores": {}
        }

        # 注入当前承诺（从表态和行动推断）
        if entity.stated_position:
            memory["commitments"].append({
                "type": "public_statement",
                "content": entity.stated_position,
                "timestamp": intelligence.collected_at
            })

        # 注入短期记忆（当前行动）
        for action in entity.current_actions:
            memory["short_term"].append({
                "type": "action",
                "content": action,
                "timestamp": intelligence.collected_at
            })

        profile["initial_memory"] = memory
        return profile

    def _instantiate_agent(self, profile: Dict) -> EntityAgent:
        """
        实例化Agent

        根据实体类型选择不同的Agent子类
        如果没有特定实现，使用 GenericEntityAgent
        """
        # 尝试导入具体的Agent类
        try:
            entity_id = profile["name"].lower().replace(" ", "_")
            module_name = f"app.services.simulation.agents.entities.{entity_id}"
            module = __import__(module_name, fromlist=[""])
            agent_class = getattr(module, f"{profile['name'].replace(' ', '')}Agent")
            agent = agent_class()
            # 更新画像
            agent.profile = profile
            return agent
        except (ImportError, AttributeError):
            # 如果没有具体实现，使用通用Agent类
            logger.warning(f"No specific agent class for {profile['name']}, using GenericEntityAgent")
            return GenericEntityAgent(profile["name"], profile)
