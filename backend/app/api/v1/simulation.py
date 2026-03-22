"""
推演 API 路由 - 新架构版本
使用领域驱动设计和应用服务层
"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from loguru import logger
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas import (
    SimulationResponse,
    SimulationList,
    SimulationConfig,
)
from app.core.redis_client import task_storage
from app.core.container import container
from app.application.simulation_service import SimulationApplicationService

router = APIRouter()

# In-memory task store (supplemental to Redis)
running_simulations: Dict[str, Dict] = {}


class SimulationRequest(BaseModel):
    """推演请求"""
    proposition: str = Field(..., description="推演命题")
    event_description: Optional[str] = Field(None, description="事件描述（兼容旧版）")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="推演配置")


async def get_simulation_service():
    """依赖注入：获取推演服务"""
    async with container.get_simulation_service() as service:
        yield service


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    service: SimulationApplicationService = Depends(get_simulation_service)
):
    """
    启动地缘政治推演
    
    Args:
        request: 推演请求，包含命题和配置
        
    Example:
        ```json
        {
          "proposition": "特朗普宣布出动地面部队攻击伊朗",
          "config": { "max_rounds": 3, "max_entities": 12 }
        }
        ```
    """
    try:
        # 优先使用 proposition，兼容旧版 event_description
        proposition = request.proposition or request.event_description
        if not proposition:
            raise HTTPException(
                status_code=400,
                detail="'proposition' or 'event_description' is required"
            )

        config = SimulationConfig(**(request.config or {}))
        
        # 使用应用服务启动推演
        simulation_id = await service.start_simulation(
            proposition=proposition,
            config=request.config or {}
        )

        logger.info(f"Started simulation [{simulation_id}]: {proposition[:80]}")

        # 初始化任务状态
        sim_data = {
            "status": "running",
            "progress": 0,
            "proposition": proposition,
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
        }
        await task_storage.save_task("simulation", simulation_id, sim_data)
        running_simulations[simulation_id] = sim_data

        # 后台执行推演（使用 LangGraph 引擎）
        async def run_background():
            try:
                # 更新进度：开始
                await task_storage.update_task(
                    "simulation", simulation_id,
                    {"status": "running", "progress": 10, "message": "正在识别实体..."}
                )
                
                # 执行推演（使用 LangGraph 引擎）
                result = await service.execute_simulation(
                    simulation_id=simulation_id,
                    proposition=proposition,
                    config=request.config or {}
                )
                
                # 更新进度：完成
                completed_data = {
                    "status": "completed",
                    "progress": 100,
                    "result": {
                        "entities_identified": [e.name for e in result.entities],
                        "simulation_rounds": [
                            {
                                "round_number": r.round_number,
                                "global_summary": r.situation_summary,
                                "decisions": [
                                    {
                                        "entity": d.entity_name,
                                        "action_type": d.action_type.value,
                                        "action_content": d.action_content,
                                        "confidence": d.confidence,
                                        "risk": d.international_risk
                                    }
                                    for d in r.decisions
                                ]
                            }
                            for r in result.rounds
                        ],
                        "final_report": result.final_report
                    },
                    "completed_at": datetime.now().isoformat(),
                }
                await task_storage.update_task("simulation", simulation_id, completed_data)
                running_simulations[simulation_id].update(completed_data)
                
                logger.info(f"Simulation {simulation_id} completed with {len(result.rounds)} rounds")
                
            except Exception as e:
                logger.error(f"Simulation {simulation_id} failed: {e}")
                await service.fail_simulation(simulation_id, str(e))
                error_data = {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now().isoformat(),
                }
                await task_storage.update_task("simulation", simulation_id, error_data)
                running_simulations[simulation_id].update(error_data)

        background_tasks.add_task(run_background)

        return SimulationResponse(
            id=UUID(simulation_id),
            event_id=UUID(simulation_id),  # 简化处理
            status="running",
            config=config,
            created_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{simulation_id}")
async def get_simulation_status(
    simulation_id: str,
    service: SimulationApplicationService = Depends(get_simulation_service)
):
    """
    获取推演状态或结果
    
    如果推演完成，返回完整结果；否则返回当前状态
    """
    # 优先从Redis获取
    sim_data = await task_storage.get_task("simulation", simulation_id)

    # 如果Redis没有，尝试从内存获取
    if sim_data is None and simulation_id in running_simulations:
        sim_data = running_simulations[simulation_id]

    # 如果都没有，尝试从数据库获取
    if sim_data is None:
        db_sim = await service.get_simulation(simulation_id)
        if db_sim:
            sim_data = db_sim

    if sim_data is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    response = {
        "id": simulation_id,
        "status": sim_data.get("status", "unknown"),
        "progress": sim_data.get("progress", 0),
        "message": "推演已完成" if sim_data.get("status") == "completed" else "推演进行中",
        "created_at": sim_data.get("created_at"),
    }

    # 如果已完成，返回结果
    if sim_data.get("status") == "completed" and sim_data.get("result"):
        response["result"] = sim_data["result"]

    # 如果失败，返回错误
    if sim_data.get("status") == "failed":
        response["error"] = sim_data.get("error", "Unknown error")
        response["message"] = "推演失败"

    return response


@router.get("/", response_model=SimulationList)
async def list_simulations(
    page: int = 1,
    page_size: int = 20,
    service: SimulationApplicationService = Depends(get_simulation_service)
):
    """获取推演列表"""
    simulations = await service.list_simulations(limit=page_size, offset=(page - 1) * page_size)
    
    return SimulationList(
        items=[
            SimulationResponse(
                id=UUID(s["id"]),
                event_id=UUID(s["id"]),
                status=s.get("status", "unknown"),
                config=SimulationConfig(**s.get("config", {})),
                created_at=datetime.fromisoformat(s["created_at"]) if s.get("created_at") else datetime.now()
            )
            for s in simulations
        ],
        total=len(simulations),
        page=page,
        page_size=page_size
    )
