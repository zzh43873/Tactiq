"""
决策引擎 - 核心领域服务

实现实体内部的鹰鸽辩论决策机制
"""
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.domain.entities import GeopoliticalEntity
from app.infrastructure.external.llm import LLMProvider, Message


class ActionType(str, Enum):
    """行动类型"""
    MILITARY = "military"
    DIPLOMATIC = "diplomatic"
    ECONOMIC = "economic"
    ENERGY = "energy"
    PUBLIC_OPINION = "public_opinion"


@dataclass
class DecisionResult:
    """决策结果"""
    entity_name: str
    action_type: ActionType
    action_content: str
    target_entities: List[str]
    reasoning: str
    confidence: float
    domestic_cost: float
    international_risk: float
    expected_outcome: str


@dataclass
class DebateContext:
    """辩论上下文"""
    proposition: str
    round_number: int
    previous_decisions: List[DecisionResult]
    other_entities: List[GeopoliticalEntity]
    situation_summary: str


class DecisionEngine:
    """
    决策引擎 - 鹰鸽辩论机制
    
    为每个实体执行三轮辩论：
    1. 鹰派顾问提出激进方案
    2. 鸽派顾问提出克制方案
    3. 最终决策者综合决策
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider
    
    async def make_decision(
        self,
        entity: GeopoliticalEntity,
        context: DebateContext
    ) -> DecisionResult:
        """执行完整决策流程"""
        # 步骤1: 鹰派分析
        hawk_argument = await self._hawk_advisor(entity, context)
        
        # 步骤2: 鸽派分析
        dove_argument = await self._dove_advisor(entity, context, hawk_argument)
        
        # 步骤3: 最终决策
        decision = await self._final_decision(entity, context, hawk_argument, dove_argument)
        
        return decision
    
    async def _hawk_advisor(
        self,
        entity: GeopoliticalEntity,
        context: DebateContext
    ) -> Dict[str, Any]:
        """鹰派顾问 - 主张激进/对抗策略"""
        system_prompt = f"""你是{entity.name}的鹰派安全顾问。

你的立场：
- 坚决捍卫国家核心利益
- 对威胁采取强硬态度
- 展示决心和力量
- 接受短期风险换取长期战略优势

你的建议应该：
1. 分析当前局势对{entity.name}的威胁
2. 提出具体的强硬反制措施
3. 说明为什么克制会损害国家利益
4. 评估行动的风险和收益

以JSON格式输出你的分析和建议。"""

        user_prompt = self._build_context_prompt(entity, context)
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = await self._llm.chat(
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse hawk advisor response", "raw": response.content}
    
    async def _dove_advisor(
        self,
        entity: GeopoliticalEntity,
        context: DebateContext,
        hawk_argument: Dict[str, Any]
    ) -> Dict[str, Any]:
        """鸽派顾问 - 主张克制/外交策略"""
        system_prompt = f"""你是{entity.name}的鸽派外交顾问。

你的立场：
- 优先考虑外交和对话
- 避免不必要的冲突升级
- 考虑国内经济和民生成本
- 寻求双赢解决方案

你的建议应该：
1. 分析鹰派方案的潜在风险
2. 提出外交替代方案
3. 说明克制如何维护长期利益
4. 评估国内政治和经济成本

以JSON格式输出你的分析和建议。"""

        user_prompt = f"""{self._build_context_prompt(entity, context)}

鹰派顾问的建议：
{json.dumps(hawk_argument, ensure_ascii=False, indent=2)}

请从鸽派角度提出你的分析和建议。"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = await self._llm.chat(
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse dove advisor response", "raw": response.content}
    
    async def _final_decision(
        self,
        entity: GeopoliticalEntity,
        context: DebateContext,
        hawk_argument: Dict[str, Any],
        dove_argument: Dict[str, Any]
    ) -> DecisionResult:
        """最终决策者 - 综合双方观点做出决策"""
        system_prompt = f"""你是{entity.name}的最高决策者。

你需要：
1. 综合考虑鹰派和鸽派顾问的建议
2. 权衡国内外各种因素
3. 做出符合国家利益的具体决策
4. 以JSON格式输出最终决策

决策必须包含以下字段：
- action_type: 行动类型 (military/diplomatic/economic/energy/public_opinion)
- action_content: 具体行动内容
- target_entities: 目标实体列表
- reasoning: 决策理由
- confidence: 信心程度 (0-1)
- domestic_cost: 国内成本评估 (0-1)
- international_risk: 国际风险 (0-1)
- expected_outcome: 预期结果"""

        user_prompt = f"""当前局势：
命题：{context.proposition}
轮次：第{context.round_number}轮

鹰派顾问建议：
{json.dumps(hawk_argument, ensure_ascii=False, indent=2)}

鸽派顾问建议：
{json.dumps(dove_argument, ensure_ascii=False, indent=2)}

请做出最终决策。"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = await self._llm.chat(
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.content)
            return DecisionResult(
                entity_name=entity.name,
                action_type=ActionType(result.get("action_type", "diplomatic")),
                action_content=result.get("action_content", "维持现状"),
                target_entities=result.get("target_entities", []),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.5),
                domestic_cost=result.get("domestic_cost", 0.5),
                international_risk=result.get("international_risk", 0.5),
                expected_outcome=result.get("expected_outcome", "")
            )
        except (json.JSONDecodeError, KeyError) as e:
            # 返回默认决策
            return DecisionResult(
                entity_name=entity.name,
                action_type=ActionType.DIPLOMATIC,
                action_content="维持观望态度，等待更多信息",
                target_entities=[],
                reasoning=f"决策解析失败: {str(e)}",
                confidence=0.3,
                domestic_cost=0.2,
                international_risk=0.2,
                expected_outcome="局势保持稳定"
            )
    
    def _build_context_prompt(
        self,
        entity: GeopoliticalEntity,
        context: DebateContext
    ) -> str:
        """构建上下文提示"""
        other_entities_str = ", ".join([e.name for e in context.other_entities])
        previous_decisions_str = ""
        if context.previous_decisions:
            previous_decisions_str = "\n".join([
                f"- {d.entity_name}: {d.action_type.value} - {d.action_content}"
                for d in context.previous_decisions[-3:]  # 只显示最近3个
            ])
        
        return f"""当前推演信息：

命题：{context.proposition}
轮次：第{context.round_number}轮

你的身份：{entity.name}
核心利益：{', '.join(entity.core_interests)}

其他参与实体：{other_entities_str}

局势摘要：
{context.situation_summary}

历史决策：
{previous_decisions_str or "无"}

请基于以上信息给出你的分析和建议。"""
