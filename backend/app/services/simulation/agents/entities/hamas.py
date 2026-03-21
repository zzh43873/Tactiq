"""
哈马斯Agent实现
"""

from typing import Dict, List
from app.services.simulation.agents.base import (
    EntityAgent, Action, Perception, Decision
)


class HamasAgent(EntityAgent):
    """哈马斯Agent - 非国家武装组织"""
    
    def __init__(self):
        profile = {
            "name": "哈马斯",
            "name_en": "Hamas",
            "type": "non_state_armed",
            "attributes": {
                "military_strength": 0.3,
                "popular_support": 0.6,
                "external_support": 0.5,
                "economic_resources": 0.2,
                "international_legitimacy": 0.1,
                "strategic_patience": 0.4,
                "risk_tolerance": 0.7
            },
            "core_interests": [
                "组织生存",
                "巴勒斯坦建国",
                "对抗以色列占领",
                "获得国际承认",
                "加沙地带控制"
            ],
            "constraints": [
                "被以色列军事压制",
                "加沙被封锁",
                "国际孤立",
                "内部派系斗争",
                "资源匮乏"
            ],
            "decision_patterns": [
                "优先使用非对称战术（火箭弹、隧道）",
                "重视舆论战和国际同情",
                "利用平民伤亡制造压力",
                "寻求地区盟友支持",
                "灵活机动，避免正面决战"
            ],
            "relationships": {
                "allies": ["伊朗", "卡塔尔", "真主党", "胡塞武装"],
                "adversaries": ["以色列", "美国", "埃及", "巴勒斯坦权力机构"],
                "complex": ["土耳其", "俄罗斯"]
            }
        }
        super().__init__("hamas", profile)
    
    def perceive(self, event: Dict, context: Dict) -> Perception:
        """
        哈马斯特有的感知逻辑
        - 对以色列行动高度敏感
        - 关注国际舆论反应
        - 评估外部支持可能性
        """
        event_type = event.get("type", "")
        actor = event.get("actor", "")
        description = event.get("description", "")
        
        threat_level = 0.0
        opportunity_level = 0.0
        affected_interests = []
        
        # 以色列的行动被视为高威胁
        if actor == "以色列" or "以色列" in description:
            if any(word in description for word in ["军事打击", "暗杀", "围困", "轰炸"]):
                threat_level = 0.9
                affected_interests.extend(["组织生存", "加沙地带控制"])
            elif any(word in description for word in ["外交压力", "制裁", "封锁"]):
                threat_level = 0.6
                affected_interests.append("组织生存")
            elif any(word in description for word in ["谈判", "停火", "协议"]):
                opportunity_level = 0.4
                affected_interests.append("巴勒斯坦建国")
        
        # 美国的行动
        if actor == "美国":
            if any(word in description for word in ["支持以色列", "军事援助", "否决"]):
                threat_level = max(threat_level, 0.7)
            elif any(word in description for word in ["施压以色列", "调解", "人道主义"]):
                opportunity_level = max(opportunity_level, 0.3)
        
        # 国际谴责以色列是机会
        if any(word in description for word in ["谴责以色列", "国际制裁", "联合国决议"]):
            opportunity_level = max(opportunity_level, 0.7)
            affected_interests.append("获得国际承认")
        
        # 伊朗支持是机会
        if any(word in description for word in ["伊朗支持", "武器援助", "资金援助"]):
            opportunity_level = max(opportunity_level, 0.6)
            affected_interests.append("组织生存")
        
        # 阿拉伯国家反应
        if any(word in description for word in ["阿拉伯国家", "海湾国家", "支持巴勒斯坦"]):
            opportunity_level = max(opportunity_level, 0.5)
        
        understanding = f"""
作为哈马斯，我对该事件的评估：
- 威胁等级: {threat_level:.1f}
- 机会等级: {opportunity_level:.1f}
- 受影响的核心利益: {', '.join(affected_interests) if affected_interests else '暂无直接威胁'}
- 关键判断: {"生存危机" if threat_level > 0.8 else "需要谨慎应对" if threat_level > 0.5 else "可寻求机会"}
"""
        
        return Perception(
            event_understanding=understanding,
            threat_assessment=threat_level,
            opportunity_assessment=opportunity_level,
            affected_interests=affected_interests
        )
    
    def decide(self, perception: Perception,
               available_actions: List[Action],
               other_agents_states: Dict) -> Decision:
        """
        哈马斯的决策逻辑
        - 生存优先
        - 寻求国际同情
        - 利用非对称优势
        """
        # 高威胁时采取防御或反击
        if perception.threat_assessment > 0.7:
            action = self._select_retaliation_action(available_actions)
            rationale = f"面临生存威胁({perception.threat_assessment:.1f})，必须坚决反击"
        # 有机会时扩大影响
        elif perception.opportunity_assessment > 0.5:
            action = self._select_propaganda_action(available_actions)
            rationale = f"存在机会窗口({perception.opportunity_assessment:.1f})，应扩大国际影响"
        # 中等威胁时采取混合策略
        elif perception.threat_assessment > 0.3:
            action = self._select_mixed_action(available_actions)
            rationale = "采取灵活策略，既展示决心又留有余地"
        else:
            action = self._select_default_action(available_actions)
            rationale = "保持低调，积蓄力量"
        
        return Decision(
            selected_action=action,
            rationale=rationale,
            alternative_considered=[a.type for a in available_actions if a != action][:3],
            confidence=0.6 if perception.threat_assessment > 0.5 else 0.4
        )
    
    def act(self, decision: Decision) -> Action:
        """执行决策"""
        return decision.selected_action
    
    def _select_retaliation_action(self, actions: List[Action]) -> Action:
        """选择报复行动"""
        # 优先选择军事反击，但保持非对称特征
        retaliation_actions = [
            a for a in actions 
            if a.type == "military" and 0.3 <= a.intensity <= 0.7
        ]
        if retaliation_actions:
            return retaliation_actions[0]
        
        # 其次选择舆论反击
        propaganda_actions = [a for a in actions if a.type == "propaganda"]
        if propaganda_actions:
            return propaganda_actions[0]
        
        return actions[0] if actions else Action(
            type="propaganda",
            target="以色列",
            content="谴责以色列的侵略行为，呼吁国际干预",
            intensity=0.5,
            expected_outcome="获得国际同情"
        )
    
    def _select_propaganda_action(self, actions: List[Action]) -> Action:
        """选择舆论行动"""
        propaganda_actions = [a for a in actions if a.type == "propaganda"]
        if propaganda_actions:
            return max(propaganda_actions, key=lambda x: x.intensity)
        
        return Action(
            type="propaganda",
            target="国际社会",
            content="展示巴勒斯坦人民的苦难，争取国际支持",
            intensity=0.7,
            expected_outcome="增加国际压力，孤立以色列"
        )
    
    def _select_mixed_action(self, actions: List[Action]) -> Action:
        """选择混合策略"""
        # 选择中等强度的行动
        mixed_actions = [
            a for a in actions 
            if 0.4 <= a.intensity <= 0.6
        ]
        if mixed_actions:
            return mixed_actions[0]
        return actions[0] if actions else self._select_default_action(actions)
    
    def _select_default_action(self, actions: List[Action]) -> Action:
        """默认行动"""
        if actions:
            return min(actions, key=lambda x: x.intensity)
        
        return Action(
            type="diplomatic",
            target=None,
            content="保持现状，观察局势发展",
            intensity=0.2,
            expected_outcome="避免不必要的冲突"
        )
