"""
演示场景API
提供预设的地缘政治推演演示场景
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from loguru import logger

from app.data.demo_scenarios import (
    list_demo_scenarios,
    get_scenario_for_api,
    SCENARIO_CONFIGS,
    DEMO_SCENARIOS
)
from app.schemas import SimulationConfig

router = APIRouter()


@router.get("/scenarios", response_model=List[Dict[str, Any]])
async def get_demo_scenarios():
    """
    获取所有演示场景列表
    
    返回预设的地缘政治推演演示场景
    """
    return list_demo_scenarios()


@router.get("/scenarios/{scenario_id}", response_model=Dict[str, Any])
async def get_scenario_detail(scenario_id: str):
    """
    获取演示场景详情
    
    Args:
        scenario_id: 场景ID
        
    Returns:
        场景详细信息，包括完整的事件描述
    """
    try:
        return get_scenario_for_api(scenario_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Scenario not found")


@router.post("/scenarios/{scenario_id}/start", response_model=Dict[str, Any])
async def start_demo_scenario(scenario_id: str):
    """
    启动演示场景推演
    
    返回启动推演所需的所有参数
    
    Args:
        scenario_id: 场景ID
        
    Returns:
        推演启动参数
    """
    try:
        scenario = get_scenario_for_api(scenario_id)
        config = SCENARIO_CONFIGS.get(scenario_id, {
            "max_rounds": 5,
            "scenarios": ["default"],
            "focus_areas": ["military", "diplomatic", "economic"]
        })
        
        return {
            "scenario": scenario,
            "config": config,
            "ready_to_start": True,
            "endpoint": "/api/v1/simulation/run",
            "method": "POST",
            "payload": {
                "event_description": scenario["event_description"],
                "config": {
                    "max_rounds": config["max_rounds"]
                }
            }
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Scenario not found")


@router.get("/scenarios/{scenario_id}/preview")
async def get_scenario_preview(scenario_id: str):
    """
    获取场景预览信息
    
    包含预期实体、关系等预览信息，用于前端展示
    """
    try:
        scenario = get_scenario_for_api(scenario_id)
        
        # 基于场景类型返回预览信息
        previews = {
            "taiwan_strait_crisis": {
                "key_entities": [
                    {"name": "中国大陆", "type": "country", "role": "initiator", "stance": "强硬"},
                    {"name": "台湾", "type": "country", "role": "target", "stance": "防御"},
                    {"name": "美国", "type": "country", "role": "ally", "stance": "介入"},
                    {"name": "日本", "type": "country", "role": "ally", "stance": "谨慎"}
                ],
                "potential_paths": [
                    "军事演习升级 → 意外冲突 → 国际调停",
                    "外交斡旋 → 局势降温 → 恢复对话",
                    "误判触发 → 有限冲突 → 第三方介入"
                ],
                "key_factors": [
                    "美国第七舰队动向",
                    "国际社会反应",
                    "地区国家立场",
                    "经济制裁影响"
                ]
            },
            "ukraine_escalation": {
                "key_entities": [
                    {"name": "乌克兰", "type": "country", "role": "target", "stance": "抵抗"},
                    {"name": "俄罗斯", "type": "country", "role": "initiator", "stance": "进攻"},
                    {"name": "北约", "type": "organization", "role": "ally", "stance": "支持"},
                    {"name": "欧盟", "type": "organization", "role": "ally", "stance": "制裁"}
                ],
                "potential_paths": [
                    "北约介入 → 冲突升级 → 核威慑",
                    "能源危机 → 内部分歧 → 谈判解决",
                    "僵持持续 → 冻结冲突 → 长期对抗"
                ],
                "key_factors": [
                    "北约直接介入可能性",
                    "核武器使用风险",
                    "欧洲能源供应",
                    "全球南方立场"
                ]
            },
            "red_sea_crisis": {
                "key_entities": [
                    {"name": "胡塞武装", "type": "non_state_actor", "role": "initiator", "stance": "对抗"},
                    {"name": "美国", "type": "country", "role": "target", "stance": "护航"},
                    {"name": "伊朗", "type": "country", "role": "adversary", "stance": "支持"},
                    {"name": "沙特", "type": "country", "role": "stakeholder", "stance": "观望"}
                ],
                "potential_paths": [
                    "护航成功 → 航运恢复 → 危机缓解",
                    "袭击持续 → 油价飙升 → 经济冲击",
                    "地区介入 → 冲突扩大 → 多方混战"
                ],
                "key_factors": [
                    "护航联盟有效性",
                    "伊朗介入程度",
                    "全球油价波动",
                    "地区大国博弈"
                ]
            }
        }
        
        return {
            "scenario_id": scenario_id,
            "title": scenario["title"],
            "preview": previews.get(scenario_id, {})
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Scenario not found")


@router.get("/featured")
async def get_featured_scenario():
    """
    获取推荐演示场景
    
    返回当前最热门的演示场景（可用于首页展示）
    """
    # 默认返回台海危机（当前最热点）
    featured = get_scenario_for_api("taiwan_strait_crisis")
    return {
        "scenario": featured,
        "reason": "当前地缘政治热点",
        "trending": True
    }


@router.get("/tags")
async def get_scenario_tags():
    """
    获取所有场景标签
    
    用于前端标签云展示
    """
    tags = {}
    for scenario in DEMO_SCENARIOS:
        for tag in scenario.tags:
            tags[tag] = tags.get(tag, 0) + 1
    
    return [
        {"tag": tag, "count": count}
        for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True)
    ]
