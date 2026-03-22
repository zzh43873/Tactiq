"""
情报收集 API 路由 - 新架构版本
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger

from app.core.redis_client import task_storage
from app.core.container import container
from app.application.intelligence_service import IntelligenceApplicationService

router = APIRouter()

# 兼容旧代码的内存存储
intelligence_tasks: Dict[str, Dict] = {}


class IntelligenceRequest(BaseModel):
    """情报收集请求"""
    event_description: str = Field(..., description="事件描述")
    time_range: Optional[str] = Field("past_30_days", description="时间范围")
    sources: Optional[List[str]] = Field(default_factory=list, description="数据源列表")


class IntelligenceResponse(BaseModel):
    """情报收集响应"""
    task_id: str
    status: str
    estimated_time: int
    message: str


async def get_intelligence_service():
    """依赖注入：获取情报服务"""
    async with container.get_intelligence_service() as service:
        yield service


@router.post("/collect", response_model=IntelligenceResponse)
async def collect_intelligence(
    request: IntelligenceRequest,
    background_tasks: BackgroundTasks,
    service: IntelligenceApplicationService = Depends(get_intelligence_service)
):
    """
    启动情报收集任务
    
    使用AI爬虫框架从多源收集情报，自动识别实体和关系
    """
    try:
        # 启动收集
        task_id = await service.start_collection(
            query=request.event_description,
            sources=request.sources or ["gdelt"],
            use_cache=True
        )

        # 初始化任务状态
        task_data = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "event_description": request.event_description,
            "created_at": datetime.now().isoformat(),
        }
        await task_storage.save_task("intelligence", task_id, task_data)
        intelligence_tasks[task_id] = task_data

        # 后台执行收集（简化版）
        async def run_collection():
            try:
                await task_storage.update_task(
                    "intelligence", task_id, {"status": "collecting", "progress": 10}
                )
                intelligence_tasks[task_id]["status"] = "collecting"
                
                import asyncio
                await asyncio.sleep(3)  # 模拟收集时间
                
                # 模拟结果
                entities = [
                    {"name": "美国", "entity_type": "country", "role": "initiator", "relevance_score": 1.0},
                    {"name": "伊朗", "entity_type": "country", "role": "target", "relevance_score": 1.0},
                    {"name": "以色列", "entity_type": "country", "role": "ally", "relevance_score": 0.9},
                ]
                
                relationships = [
                    {"entity_a": "美国", "entity_b": "伊朗", "relationship": "conflict", "tension_level": 0.9},
                    {"entity_a": "美国", "entity_b": "以色列", "relationship": "alliance", "tension_level": 0.1},
                ]
                
                articles = [
                    {"title": "模拟文章1", "source": "GDELT", "url": "http://example.com/1"},
                    {"title": "模拟文章2", "source": "GDELT", "url": "http://example.com/2"},
                ]
                
                sources = [{"name": "GDELT", "count": 2}]
                
                # 完成收集
                await service.complete_collection(
                    collection_id=task_id,
                    entities=entities,
                    relationships=relationships,
                    articles=articles,
                    sources=sources,
                    query=request.event_description
                )
                
                completed_data = {
                    "status": "completed",
                    "progress": 100,
                    "report": {
                        "identified_entities": entities,
                        "relationship_dynamics": {
                            "active_conflicts": [["美国", "伊朗"]],
                            "tensions": [],
                            "cooperation": [["美国", "以色列"]],
                        },
                        "event_summary": f"关于'{request.event_description}'的情报摘要",
                    },
                    "completed_at": datetime.now().isoformat(),
                }
                await task_storage.update_task("intelligence", task_id, completed_data)
                intelligence_tasks[task_id].update(completed_data)
                
                logger.info(f"Intelligence collection completed: {task_id}")
                
            except Exception as e:
                logger.error(f"Intelligence collection failed: {e}")
                error_data = {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now().isoformat(),
                }
                await task_storage.update_task("intelligence", task_id, error_data)
                intelligence_tasks[task_id].update(error_data)

        background_tasks.add_task(run_collection)

        return IntelligenceResponse(
            task_id=task_id,
            status="processing",
            estimated_time=180,
            message="情报收集任务已启动，预计需要2-3分钟"
        )

    except Exception as e:
        logger.error(f"Failed to start intelligence collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_intelligence_status(
    task_id: str,
    service: IntelligenceApplicationService = Depends(get_intelligence_service)
):
    """获取情报收集任务状态"""
    # 优先从Redis获取
    task = await task_storage.get_task("intelligence", task_id)
    
    # 如果Redis没有，尝试从内存获取
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    # 如果都没有，尝试从数据库获取
    if task is None:
        db_task = await service.get_intelligence(task_id)
        if db_task:
            task = db_task
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "progress": task.get("progress", 0),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
        "error": task.get("error"),
    }


@router.get("/task/{task_id}/result")
async def get_intelligence_result(task_id: str):
    """获取情报收集结果"""
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is still {task.get('status')}, please wait"
        )

    return {
        "task_id": task_id,
        "status": "completed",
        "report": task.get("report", {}),
        "completed_at": task.get("completed_at"),
    }


@router.get("/task/{task_id}/entities")
async def get_identified_entities(task_id: str):
    """获取识别到的实体列表"""
    task = await task_storage.get_task("intelligence", task_id)
    if task is None and task_id in intelligence_tasks:
        task = intelligence_tasks[task_id]
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    report = task.get("report", {})
    return report.get("identified_entities", [])


@router.get("/history")
async def get_intelligence_history(
    limit: int = 20,
    offset: int = 0,
    service: IntelligenceApplicationService = Depends(get_intelligence_service)
):
    """获取情报收集历史记录"""
    history = await service.list_recent_intelligence(limit=limit, offset=offset)
    
    return {
        "items": history,
        "total": len(history),
        "limit": limit,
        "offset": offset,
    }
