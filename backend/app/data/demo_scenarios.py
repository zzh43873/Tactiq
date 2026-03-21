"""
演示场景数据
为产品发布准备的3个地缘政治推演场景
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class DemoScenario:
    """演示场景"""
    id: str
    title: str
    title_en: str
    description: str
    event_description: str
    tags: List[str]
    expected_entities: List[str]
    complexity: str  # simple/medium/complex
    estimated_time: int  # 预计推演时间（秒）
    icon: str  # emoji图标


# 演示场景列表
DEMO_SCENARIOS: List[DemoScenario] = [
    DemoScenario(
        id="taiwan_strait_crisis",
        title="台海危机72小时",
        title_en="Taiwan Strait Crisis: 72 Hours",
        description="模拟台海突发军事冲突情景，推演各方在72小时内的决策连锁反应",
        event_description="""
台海突发军事冲突情景推演：

背景：
- 某日上午，台海地区突发军事摩擦
- 大陆方面宣布在台海周边进行大规模军事演习
- 美国第七舰队进入台湾海峡"自由航行"
- 日本宣布启动撤侨行动

关键问题：
1. 冲突会在72小时内如何升级或降温？
2. 各方（中国大陆、台湾、美国、日本）可能采取什么行动？
3. 国际社会的反应会如何影响局势？
4. 最可能的情景路径是什么？

请推演未来72小时的地缘政治连锁反应。
        """.strip(),
        tags=["台海", "军事冲突", "大国博弈", "实时热点"],
        expected_entities=["中国大陆", "台湾", "美国", "日本", "菲律宾", "澳大利亚"],
        complexity="complex",
        estimated_time=180,
        icon="⚡"
    ),
    
    DemoScenario(
        id="ukraine_escalation",
        title="乌克兰冲突外溢效应",
        title_en="Ukraine Conflict Spillover",
        description="推演乌克兰冲突升级对欧洲能源、北约、全球粮食安全的多维度影响",
        event_description="""
乌克兰冲突升级情景推演：

背景：
- 乌克兰冲突进入第三年，战局陷入僵持
- 北约国家考虑直接军事介入
- 俄罗斯威胁使用战术核武器
- 欧洲能源危机加剧，多国出现社会动荡

关键问题：
1. 北约直接介入会如何改变战局？
2. 核威胁是虚张声势还是真实风险？
3. 欧洲能源危机如何影响各国对乌支持？
4. 全球南方国家（中国、印度、巴西）会如何选择立场？
5. 冲突外溢的最危险路径是什么？

请推演乌克兰冲突升级的多维度连锁反应。
        """.strip(),
        tags=["乌克兰", "北约", "能源危机", "核威胁"],
        expected_entities=["乌克兰", "俄罗斯", "美国", "德国", "法国", "中国", "波兰"],
        complexity="medium",
        estimated_time=150,
        icon="🔥"
    ),
    
    DemoScenario(
        id="red_sea_crisis",
        title="红海航运危机",
        title_en="Red Sea Shipping Crisis",
        description="推演胡塞武装袭击红海航运对全球贸易、油价、地区安全的连锁影响",
        event_description="""
红海航运危机情景推演：

背景：
- 胡塞武装持续袭击红海国际航运
- 多家国际航运公司宣布暂停红海航线
- 美国组建多国护航联盟
- 伊朗被指控支持胡塞武装
- 全球油价上涨15%

关键问题：
1. 护航联盟能否有效保护航运安全？
2. 伊朗会如何回应国际压力？
3. 沙特、阿联酋等地区大国会采取什么立场？
4. 全球贸易和油价会受到多大影响？
5. 以色列-哈马斯冲突会如何与此互动？

请推演红海危机对全球贸易和地区安全的连锁影响。
        """.strip(),
        tags=["红海", "航运危机", "胡塞武装", "全球贸易"],
        expected_entities=["胡塞武装", "美国", "伊朗", "沙特", "以色列", "埃及", "中国"],
        complexity="medium",
        estimated_time=120,
        icon="🚢"
    ),
]


def get_demo_scenario(scenario_id: str) -> DemoScenario:
    """获取指定演示场景"""
    for scenario in DEMO_SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


def list_demo_scenarios() -> List[Dict[str, Any]]:
    """列出所有演示场景"""
    return [
        {
            "id": s.id,
            "title": s.title,
            "title_en": s.title_en,
            "description": s.description,
            "tags": s.tags,
            "complexity": s.complexity,
            "estimated_time": s.estimated_time,
            "icon": s.icon
        }
        for s in DEMO_SCENARIOS
    ]


def get_scenario_for_api(scenario_id: str) -> Dict[str, Any]:
    """获取API格式的场景数据"""
    scenario = get_demo_scenario(scenario_id)
    return {
        "id": scenario.id,
        "title": scenario.title,
        "title_en": scenario.title_en,
        "description": scenario.description,
        "event_description": scenario.event_description,
        "tags": scenario.tags,
        "expected_entities": scenario.expected_entities,
        "complexity": scenario.complexity,
        "estimated_time": scenario.estimated_time,
        "icon": scenario.icon
    }


# 场景推荐配置（用于前端快速启动）
SCENARIO_CONFIGS = {
    "taiwan_strait_crisis": {
        "max_rounds": 5,
        "scenarios": ["escalation", "de-escalation", "stalemate"],
        "focus_areas": ["military", "diplomatic", "economic"]
    },
    "ukraine_escalation": {
        "max_rounds": 4,
        "scenarios": ["nato_intervention", "negotiated_settlement", "frozen_conflict"],
        "focus_areas": ["military", "energy", "humanitarian"]
    },
    "red_sea_crisis": {
        "max_rounds": 4,
        "scenarios": ["successful_escort", "protracted_crisis", "regional_war"],
        "focus_areas": ["economic", "military", "diplomatic"]
    }
}
