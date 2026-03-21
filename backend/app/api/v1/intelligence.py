"""
情报收集API路由
集成AI爬虫框架
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from loguru import logger
import uuid

from app.schemas import (
    IntelligenceRequest,
    IntelligenceResponse,
    EventAnalysis,
    EntityStance,
    DimensionImpact
)
from app.services.intelligence.collector import IntelligenceCollector, IntelligenceReport
from app.db.session import get_db
from app.core.redis_client import task_storage

router = APIRouter()

# 兼容旧代码：内存任务存储（已迁移到Redis）
# 保留引用以便其他模块导入
intelligence_tasks: Dict[str, Dict] = {}


class IntelligenceResult(BaseModel):
    """情报收集结果"""
    task_id: str
    status: str
    report: Optional[Dict] = None
    entities: List[Dict] = []
    relationships: Dict = {}
    sources: List[Dict] = []
    raw_contents: List[Dict] = []  # 新增：原始收集内容
    completed_at: Optional[datetime] = None


async def run_intelligence_collection(task_id: str, event_description: str):
    """后台运行情报收集任务"""
    try:
        # 更新Redis中的任务状态
        await task_storage.update_task("intelligence", task_id, {
            "status": "collecting",
            "progress": 10
        })
        # 同时更新内存（兼容旧代码）
        if task_id in intelligence_tasks:
            intelligence_tasks[task_id]["status"] = "collecting"
            intelligence_tasks[task_id]["progress"] = 10

        # 初始化收集器
        collector = IntelligenceCollector()

        await task_storage.update_task("intelligence", task_id, {"progress": 20})
        if task_id in intelligence_tasks:
            intelligence_tasks[task_id]["progress"] = 20

        # 执行情报收集
        report = await collector.collect(event_description)
        
        # 保存原始内容用于前端展示
        raw_contents = []
        if hasattr(collector, 'last_raw_contents'):
            raw_contents = [
                {
                    "source": content.raw.source,
                    "title": content.raw.title,
                    "url": content.raw.url,
                    "content": content.raw.content[:500] + "..." if len(content.raw.content) > 500 else content.raw.content,
                    "published_at": content.raw.published_at.isoformat() if content.raw.published_at else None,
                    "relevance_score": content.relevance_score,
                    "sentiment": content.sentiment,
                    "summary": content.summary
                }
                for content in collector.last_raw_contents[:20]  # 限制数量
            ]
        
        # 保存预识别实体和扩展查询
        pre_identified_entities = getattr(collector, 'pre_identified_entities', [])
        pre_identified_relationships = getattr(collector, 'pre_identified_relationships', [])
        expanded_queries = []
        if hasattr(collector, 'last_expansion_result') and collector.last_expansion_result:
            expanded_queries = [
                {
                    "query": q.query,
                    "query_type": q.query_type,
                    "rationale": q.rationale,
                    "priority": q.priority
                }
                for q in collector.last_expansion_result.expanded_queries
            ]

        await task_storage.update_task("intelligence", task_id, {"progress": 80})
        if task_id in intelligence_tasks:
            intelligence_tasks[task_id]["progress"] = 80

        # 转换为字典格式
        report_dict = {
            "event_summary": report.event_summary,
            "timeframe": report.timeframe,
            "background": report.background,
            "identified_entities": [
                {
                    "name": e.name,
                    "name_en": e.name_en,
                    "entity_type": e.entity_type,
                    "role": e.role,
                    "relevance_score": e.relevance_score,
                    "current_actions": e.current_actions,
                    "stated_position": e.stated_position,
                    "key_interests": e.key_interests
                }
                for e in report.identified_entities
            ],
            "relationship_dynamics": {
                "active_conflicts": report.relationship_dynamics.active_conflicts,
                "tensions": report.relationship_dynamics.tensions,
                "cooperation": report.relationship_dynamics.cooperation,
                "key_relationships": getattr(report.relationship_dynamics, 'key_relationships', [])
            },
            "military_deployments": report.military_deployments,
            "diplomatic_activities": report.diplomatic_activities,
            "economic_measures": report.economic_measures,
            "sources": report.sources,
            "confidence_level": report.confidence_level,
            "collected_at": report.collected_at.isoformat()
        }

        # 更新任务状态
        completed_data = {
            "status": "completed",
            "progress": 100,
            "report": report_dict,
            "raw_contents": raw_contents,
            "pre_identified_entities": pre_identified_entities,
            "pre_identified_relationships": pre_identified_relationships,
            "expanded_queries": expanded_queries,
            "completed_at": datetime.now()
        }
        await task_storage.update_task("intelligence", task_id, completed_data)
        intelligence_tasks[task_id].update(completed_data)

        await collector.close()
        logger.info(f"Intelligence collection completed for task {task_id}")

    except Exception as e:
        logger.error(f"Intelligence collection failed for task {task_id}: {e}")
        error_data = {
            "status": "failed",
            "error": str(e),
            "progress": 0
        }
        await task_storage.update_task("intelligence", task_id, error_data)
        intelligence_tasks[task_id].update(error_data)


@router.post("/collect", response_model=IntelligenceResponse)
async def collect_intelligence(
    request: IntelligenceRequest,
    background_tasks: BackgroundTasks
):
    """
    启动情报收集任务

    使用AI爬虫框架从多源收集情报，自动识别实体和关系

    - **event_description**: 事件描述（如"美国出兵伊朗的推演"）
    - **time_range**: 时间范围 (past_7_days, past_30_days, past_90_days)
    - **sources**: 数据源列表 (gdelt, newsapi)
    """
    try:
        task_id = f"intel_{uuid.uuid4().hex[:12]}"

        # 初始化任务状态（同时保存到Redis和内存）
        task_data = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "event_description": request.event_description,
            "created_at": datetime.now()
        }
        await task_storage.save_task("intelligence", task_id, task_data)
        intelligence_tasks[task_id] = task_data

        logger.info(f"Starting intelligence collection task {task_id}: {request.event_description[:50]}...")

        # 后台执行收集任务
        background_tasks.add_task(
            run_intelligence_collection,
            task_id,
            request.event_description
        )

        return IntelligenceResponse(
            task_id=task_id,
            status="processing",
            estimated_time=180,
            message="情报收集任务已启动，预计需要2-3分钟"
        )

    except Exception as e:
        logger.error(f"Failed to start intelligence collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=Dict)
async def get_intelligence_status(task_id: str):
    """
    获取情报收集任务状态

    返回任务进度和结果
    """
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    
    # 如果Redis没有，尝试从内存获取（兼容旧任务）
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task.get("progress", 0),
        "created_at": task["created_at"].isoformat() if task.get("created_at") else None,
        "completed_at": task["completed_at"].isoformat() if task.get("completed_at") else None,
        "error": task.get("error")
    }


@router.get("/task/{task_id}/result", response_model=Dict)
async def get_intelligence_result(task_id: str):
    """
    获取情报收集结果

    返回完整的情报报告，包括识别的实体、关系、态势等
    """
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is still {task['status']}, please wait"
        )

    return {
        "task_id": task_id,
        "status": "completed",
        "report": task.get("report"),
        "completed_at": task["completed_at"].isoformat() if task.get("completed_at") else None
    }


@router.get("/task/{task_id}/contents", response_model=List[Dict])
async def get_collected_contents(task_id: str):
    """
    获取收集到的原始内容
    
    返回情报收集过程中获取的原始文章内容，用于前端展示
    """
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 如果任务已完成，返回保存的原始内容
    if task["status"] == "completed":
        return task.get("raw_contents", [])
    
    # 如果任务还在进行中，返回当前进度信息
    return [{
        "status": task["status"],
        "progress": task.get("progress", 0),
        "message": "情报收集进行中，请稍候..."
    }]
# 模拟实体数据（用于前端调试）
MOCK_ENTITIES = [
    {
        "name": "美国",
        "entity_type": "country",
        "role": "target",
        "relevance_score": 1.0,
        "rationale": "冲突的直接目标方，本土遭受打击",
        "key_interests": ["本土安全", "全球霸权维护", "盟友保护"],
        "current_actions": ["全国动员", "军事部署"]
    },
    {
        "name": "伊朗",
        "entity_type": "country",
        "role": "initiator",
        "relevance_score": 1.0,
        "rationale": "冲突的发起方，主动打击美国本土",
        "key_interests": ["政权生存", "地区影响力", "核计划保护"],
        "current_actions": ["导弹发射", "代理人动员"]
    },
    {
        "name": "以色列",
        "entity_type": "country",
        "role": "ally",
        "relevance_score": 0.95,
        "rationale": "美国在中东最紧密盟友",
        "key_interests": ["国家安全", "消除伊朗核威胁"],
        "current_actions": ["防御准备", "情报共享"]
    },
    {
        "name": "沙特阿拉伯",
        "entity_type": "country",
        "role": "regional_actor",
        "relevance_score": 0.9,
        "rationale": "地区主要大国，拥有美军基地",
        "key_interests": ["王室安全", "石油设施保护"],
        "current_actions": ["外交斡旋"]
    },
    {
        "name": "俄罗斯",
        "entity_type": "country",
        "role": "adversary",
        "relevance_score": 0.9,
        "rationale": "伊朗的战略合作伙伴",
        "key_interests": ["削弱美国影响力", "保护叙利亚利益"],
        "current_actions": ["外交支持", "情报协助"]
    },
    {
        "name": "中国",
        "entity_type": "country",
        "role": "economic_stakeholder",
        "relevance_score": 0.85,
        "rationale": "伊朗主要石油买家，全球第二大经济体",
        "key_interests": ["能源供应稳定", "贸易通道安全"],
        "current_actions": ["呼吁克制", "外交调解"]
    },
    {
        "name": "真主党",
        "entity_type": "non_state_actor",
        "role": "military_actor",
        "relevance_score": 0.85,
        "rationale": "伊朗最强大代理人",
        "key_interests": ["抵抗轴心", "黎巴嫩政治影响力"],
        "current_actions": ["火箭弹袭击", "边境冲突"]
    },
    {
        "name": "胡塞武装",
        "entity_type": "non_state_actor",
        "role": "military_actor",
        "relevance_score": 0.8,
        "rationale": "控制红海航道",
        "key_interests": ["也门控制权", "封锁以色列贸易"],
        "current_actions": ["海上封锁", "导弹袭击"]
    }
]

MOCK_RELATIONSHIPS = [
    {"entity_a": "美国", "entity_b": "伊朗", "relationship": "conflict", "tension_level": 1.0},
    {"entity_a": "美国", "entity_b": "以色列", "relationship": "alliance", "tension_level": 0.0},
    {"entity_a": "伊朗", "entity_b": "真主党", "relationship": "proxy", "tension_level": 0.2},
    {"entity_a": "伊朗", "entity_b": "胡塞武装", "relationship": "proxy", "tension_level": 0.2},
    {"entity_a": "俄罗斯", "entity_b": "伊朗", "relationship": "cooperation", "tension_level": 0.3},
    {"entity_a": "中国", "entity_b": "美国", "relationship": "tension", "tension_level": 0.6}
]


@router.get("/task/{task_id}/entities", response_model=List[Dict])
async def get_identified_entities(task_id: str):
    """
    获取识别到的实体列表

    返回情报收集中自动识别的所有实体（从文章内容中提取）
    """
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    report = task.get("report", {})
    entities = report.get("identified_entities", [])
    
    return entities


@router.get("/task/{task_id}/pre-entities", response_model=Dict)
async def get_pre_identified_entities(task_id: str):
    """
    获取预识别的实体列表（LLM预识别阶段）

    返回查询扩展阶段LLM预识别的所有实体和关系
    这些实体在情报收集开始阶段就已识别，可用于前端早期展示
    """
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 返回预识别实体和关系
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "pre_identified_entities": task.get("pre_identified_entities", []),
        "pre_identified_relationships": task.get("pre_identified_relationships", []),
        "expanded_queries": task.get("expanded_queries", [])
    }


@router.get("/task/{task_id}/analysis", response_model=EventAnalysis)
async def get_event_analysis(task_id: str):
    """
    获取事件分析结果

    基于收集的情报生成事件分析
    """
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is still {task['status']}, please wait"
        )

    report = task.get("report", {})
    entities_data = report.get("identified_entities", [])

    # 转换为EntityStance格式
    entities = []
    for e in entities_data:
        # 根据role确定立场
        stance = 0.0
        if e.get("role") == "initiator":
            stance = 0.5
        elif e.get("role") == "target":
            stance = -0.5
        elif e.get("role") == "ally":
            stance = 0.3

        entity = EntityStance(
            entity_id=uuid.uuid4(),  # 生成临时ID
            entity_name=e.get("name", ""),
            stance=stance,
            interest_relevance="高" if e.get("relevance_score", 0) > 0.7 else "中",
            action_willingness="高" if len(e.get("current_actions", [])) > 0 else "中",
            key_interests=e.get("key_interests", [])
        )
        entities.append(entity)

    # 计算升级可能性
    conflicts = report.get("relationship_dynamics", {}).get("active_conflicts", [])
    tensions = report.get("relationship_dynamics", {}).get("tensions", [])
    potential_escalation = min(0.9, (len(conflicts) * 0.3 + len(tensions) * 0.1))

    return EventAnalysis(
        event_id=uuid.uuid4(),
        entities=entities,
        key_factors=report.get("background", "").split("\n")[:5],
        potential_escalation=potential_escalation,
        summary=report.get("event_summary", "")
    )


@router.post("/quick-analyze", response_model=Dict)
async def quick_analyze(request: IntelligenceRequest):
    """
    快速分析（同步接口）

    直接返回分析结果，适用于简单查询
    """
    try:
        collector = IntelligenceCollector()

        logger.info(f"Starting quick analysis: {request.event_description[:50]}...")

        # 执行情报收集
        report = await collector.collect(request.event_description)

        await collector.close()

        # 简化返回结果
        return {
            "status": "completed",
            "entities": [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "role": e.role,
                    "relevance": e.relevance_score
                }
                for e in report.identified_entities[:10]  # 只返回前10个
            ],
            "relationships": {
                "conflicts": report.relationship_dynamics.active_conflicts,
                "tensions": report.relationship_dynamics.tensions,
                "cooperation": report.relationship_dynamics.cooperation
            },
            "summary": report.event_summary,
            "confidence": report.confidence_level,
            "sources_count": len(report.sources)
        }

    except Exception as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=Dict)
async def get_intelligence_history(
    limit: int = 20,
    offset: int = 0,
    db=Depends(get_db)
):
    """
    获取情报收集历史记录

    返回之前收集过的情报记录，支持分页
    
    参数:
        limit: 返回数量限制（默认20）
        offset: 偏移量（默认0）
    """
    try:
        from app.services.intelligence.cache_service import IntelligenceCacheService
        
        cache_service = IntelligenceCacheService(db)
        history = await cache_service.get_history(limit=limit, offset=offset)
        
        logger.info(f"Retrieved {len(history)} history records")
        
        return {
            "items": [cache.to_dict() for cache in history],
            "total": len(history),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
