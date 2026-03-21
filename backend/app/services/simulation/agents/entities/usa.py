"""
美国Agent实现
"""

from typing import Dict, List
from app.services.simulation.agents.base import (
    EntityAgent, Action, Perception, Decision
)


class USAAgent(EntityAgent):
    """美国Agent - 超级大国"""
    
    def __init__(self):
        profile = {
            "name": "美国",
            "name_en": "United States",
            "type": "sovereign_state",
            "attributes": {
                "economic_power": 0.95,
                "military_power": 0.95,
                "diplomatic_influence": 0.9,
                "domestic_stability": 0.7,
                "strategic_patience": 0.6,
                "risk_tolerance": 0.5,
                "technological_leadership": 0.9
            },
            "core_interests": [
                "全球霸权地位",
                "盟友体系稳定",
                "经济主导地位",
                "技术领先优势",
                "国内政治稳定",
                "能源安全"
            ],
            "constraints": [
                "国内政治极化",
                "选民疲劳",
                "预算赤字",
                "多线作战风险",
                "盟友协调成本"
            ],
            "decision_patterns": [
                "优先考虑联盟协调",
                "经济制裁优先于军事干预",
                "避免直接大国冲突",
                "重视国内舆论反应",
                "利用多边机制"
            ],
            "relationships": {
                "allies": ["北约", "日本", "韩国", "澳大利亚", "以色列", "沙特"],
                "adversaries": ["中国", "俄罗斯", "伊朗", "朝鲜"],
                "complex": ["土耳其", "印度", "巴基斯坦"]
            }
        }
        super().__init__("usa", profile)
    
    def perceive(self, event: Dict, context: Dict) -> Perception:
        """
        美国的感知逻辑
        - 关注全球影响
        - 考虑盟友反应
        - 评估国内政治影响
        """
        event_type = event.get("type", "")
        actor = event.get("actor", "")
        description = event.get("description", "")
        
        threat_level = 0.0
        opportunity_level = 0.0
        affected_interests = []
        
        # 对手的行动
        if actor in ["中国", "俄罗斯", "伊朗", "朝鲜"]:
            if any(word in description for word in ["军事扩张", "核武器", "威胁盟友"]):
                threat_level = 0.8
                affected_interests.extend(["全球霸权地位", "盟友体系稳定"])
            elif any(word in description for word in ["经济竞争", "技术竞争", "制裁"]):
                threat_level = 0.6
                affected_interests.extend(["经济主导地位", "技术领先优势"])
        
        # 盟友受攻击
        if actor in self.profile["relationships"]["allies"]:
            if any(word in description for word in ["受攻击", "被威胁", "危机"]):
                threat_level = max(threat_level, 0.7)
                affected_interests.append("盟友体系稳定")
        
        # 中东局势
        if any(word in description for word in ["以色列", "哈马斯", "真主党", "伊朗"]):
            if "冲突升级" in description or "战争" in description:
                threat_level = max(threat_level, 0.6)
                affected_interests.extend(["盟友体系稳定", "能源安全"])
        
        # 机会识别
        if any(word in description for word in ["对手失误", "内部分裂", "经济困难"]):
            opportunity_level = 0.5
        
        # 国内政治因素
        if any(word in description for word in ["选举", "民意", "国会"]):
            affected_interests.append("国内政治稳定")
        
        understanding = f"""
作为美国，我对该事件的评估：
- 威胁等级: {threat_level:.1f}
- 机会等级: {opportunity_level:.1f}
- 受影响的核心利益: {', '.join(affected_interests) if affected_interests else '暂无直接威胁'}
- 关键考虑: {"需要坚决回应" if threat_level > 0.7 else "需要谨慎评估" if threat_level > 0.4 else "可保持观望"}
- 盟友协调: {"需要紧急协调盟友立场" if threat_level > 0.6 else "保持常规沟通"}
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
        美国的决策逻辑
        - 联盟协调
        - 经济制裁优先
        - 避免直接军事冲突（除非核心利益）
        """
        # 高威胁时采取强硬但克制的回应
        if perception.threat_assessment > 0.7:
            # 优先选择外交+经济组合拳
            action = self._select_strong_response(available_actions)
            rationale = f"面临重大威胁({perception.threat_assessment:.1f})，需要坚决但审慎的回应"
        
        # 中等威胁时采取外交施压
        elif perception.threat_assessment > 0.4:
            action = self._select_diplomatic_pressure(available_actions)
            rationale = "通过外交和经济手段施加压力"
        
        # 有机会时扩大影响
        elif perception.opportunity_assessment > 0.5:
            action = self._select_opportunity_action(available_actions)
            rationale = "抓住机会扩大影响力"
        
        else:
            action = self._select_default_action(available_actions)
            rationale = "保持战略耐心，观察局势发展"
        
        return Decision(
            selected_action=action,
            rationale=rationale,
            alternative_considered=[a.type for a in available_actions if a != action][:3],
            confidence=0.7 if perception.threat_assessment > 0.5 else 0.5
        )
    
    def act(self, decision: Decision) -> Action:
        """执行决策"""
        return decision.selected_action
    
    def _select_strong_response(self, actions: List[Action]) -> Action:
        """选择强硬回应"""
        # 优先选择经济制裁
        economic_actions = [
            a for a in actions 
            if a.type == "economic" and a.intensity >= 0.6
        ]
        if economic_actions:
            return economic_actions[0]
        
        # 其次选择军事威慑（但不直接冲突）
        military_actions = [
            a for a in actions 
            if a.type == "military" and 0.4 <= a.intensity <= 0.7
        ]
        if military_actions:
            return military_actions[0]
        
        # 外交施压
        diplomatic_actions = [a for a in actions if a.type == "diplomatic"]
        if diplomatic_actions:
            return max(diplomatic_actions, key=lambda x: x.intensity)
        
        return actions[0] if actions else Action(
            type="diplomatic",
            target=None,
            content="发表声明，表达严重关切",
            intensity=0.5,
            expected_outcome="展示立场，威慑对手"
        )
    
    def _select_diplomatic_pressure(self, actions: List[Action]) -> Action:
        """选择外交施压"""
        diplomatic_actions = [a for a in actions if a.type == "diplomatic"]
        if diplomatic_actions:
            return diplomatic_actions[0]
        
        economic_actions = [
            a for a in actions 
            if a.type == "economic" and a.intensity <= 0.5
        ]
        if economic_actions:
            return economic_actions[0]
        
        return Action(
            type="diplomatic",
            target=None,
            content="通过多边机制施压",
            intensity=0.4,
            expected_outcome="孤立对手，争取国际支持"
        )
    
    def _select_opportunity_action(self, actions: List[Action]) -> Action:
        """选择机会行动"""
        # 扩大影响力
        influence_actions = [a for a in actions if a.type in ["diplomatic", "economic"]]
        if influence_actions:
            return max(influence_actions, key=lambda x: x.intensity)
        
        return actions[0] if actions else self._select_default_action(actions)
    
    def _select_default_action(self, actions: List[Action]) -> Action:
        """默认行动"""
        if actions:
            return min(actions, key=lambda x: x.intensity)
        
        return Action(
            type="diplomatic",
            target=None,
            content="保持观望，收集情报",
            intensity=0.2,
            expected_outcome="避免过早承诺"
        )
