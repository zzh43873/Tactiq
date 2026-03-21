"""
推演 API 路由 - 支持新架构（情报驱动 + 动态Agent构建）
"""

from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger
from datetime import datetime

from app.schemas import (
    SimulationResponse,
    SimulationList,
    SimulationConfig
)
from app.core.redis_client import task_storage

router= APIRouter()

# 存储运行中的推演任务（已迁移到Redis）
running_simulations: Dict[str, Dict] = {}

# 导入情报任务存储（统一存储）
from app.api.v1.intelligence import intelligence_tasks


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(
   request: Dict[str, Any],
   background_tasks: BackgroundTasks
):
    """
    运行地缘政治推演（新流程）
    
    **新流程说明**：
    1. 用户只需输入事件描述（命题），如"美国出兵伊朗的推演"
    2. 系统自动收集情报、识别相关实体
    3. 动态构建相关 Agent（以色列、伊朗、真主党、沙特等）
    4. 执行多轮推演
    5. 返回结果
    
    **请求示例**：
    ```json
    {
      "event_description": "美国出兵伊朗的推演",
      "config": {
        "max_rounds": 5,
        "scenarios": ["cooperative", "confrontational", "mixed"]
      }
    }
    ```
    
    **与旧 API 的区别**：
    - 不再需要预先指定 event_id
    - 不再需要手动指定 participating_entities
    - 系统自动识别和构建相关方
    """
    try:
        event_description = request.get("event_description")
        if not event_description:
            raise HTTPException(status_code=400, detail="event_description is required")

        config_dict = request.get("config", {})
        config = SimulationConfig(**config_dict)

        import uuid
        from datetime import datetime
        
        # 生成真实的UUID
        simulation_id = uuid.uuid4()
        event_id = uuid.uuid4()
        
        logger.info(f"Starting simulation for: {event_description}")
        
        # 初始化任务状态（立即返回，避免前端404）
        sim_data = {
            "status": "collecting",
            "progress": 0,
            "event_description": event_description,
            "created_at": datetime.now(),
            "result": None,
            "error": None
        }
        await task_storage.save_task("simulation", str(simulation_id), sim_data)
        running_simulations[str(simulation_id)] = sim_data
        
        # 创建推演控制器
        from app.services.simulation.orchestrator import SimulationOrchestrator
        orchestrator = SimulationOrchestrator(config)
        
        # 在后台运行推演
        async def run_background():
            from app.db.session import AsyncSessionLocal
            from app.services.intelligence.cache_service import IntelligenceCacheService
            from app.services.intelligence.collector import IntelligenceCollector
            from app.services.intelligence.framework.query_expander import QueryExpander
            
            # 初始化变量，确保在所有路径中都可用
            pre_identified_entities = []
            pre_identified_relationships = []
            expanded_queries = []
            
            try:
                # 同时在情报任务中注册（让前端可以查询情报收集状态）
                intelligence_tasks[str(simulation_id)] = {
                    "task_id": str(simulation_id),
                    "status": "collecting",
                    "progress": 5,
                    "event_description": event_description,
                    "created_at": datetime.now(),
                    "pre_identified_entities": [],
                    "pre_identified_relationships": [],
                    "expanded_queries": []
                }
                
                # 更新推演状态
                running_simulations[str(simulation_id)]["status"] = "collecting"
                running_simulations[str(simulation_id)]["progress"] = 5
                
                # 首先检查数据库中是否已有缓存
                async with AsyncSessionLocal() as db:
                    cache_service = IntelligenceCacheService(db)
                    cache_status = await cache_service.get_cache_status(event_description)
                    
                    if cache_status["exists"]:
                        logger.info(f"Found existing cache for: {event_description[:50]}...")
                        cached = cache_status["cache"]
                        
                        # 使用缓存的预识别数据
                        pre_identified_entities = cached.pre_identified_entities or []
                        pre_identified_relationships = cached.pre_identified_relationships or []
                        expanded_queries = cached.expanded_queries or []
                        
                        intelligence_tasks[str(simulation_id)].update({
                            "progress": 15,
                            "pre_identified_entities": pre_identified_entities,
                            "pre_identified_relationships": pre_identified_relationships,
                            "expanded_queries": expanded_queries
                        })
                        
                        running_simulations[str(simulation_id)]["progress"] = 15
                        
                        # 如果缓存是新鲜的，直接使用缓存的情报数据
                        # 但如果有缓存的推演结果，也一并返回
                        if cache_status["is_fresh"]:
                            logger.info("Using fresh cached data, skipping LLM calls")
                            
                            # 从缓存重建报告
                            collector = IntelligenceCollector()
                            report = collector._cache_to_report(cached)
                            
                            # 检查缓存中是否有推演结果
                            cached_simulation_result = cached.simulation_result if cached else None
                            
                            # 更新缓存命中次数
                            await cache_service.get_cache(event_description)
                            
                            # 如果有缓存的推演结果，直接使用并返回
                            if cached_simulation_result and cached_simulation_result.get('paths'):
                                logger.info(f"Using cached simulation result with {len(cached_simulation_result.get('paths', []))} paths")
                                
                                # 更新任务状态为完成
                                intelligence_tasks[str(simulation_id)].update({
                                    "status": "completed",
                                    "progress": 100,
                                    "report": {
                                        "identified_entities": cached.identified_entities or []
                                    },
                                    "raw_contents": cached.collected_articles or [],
                                    "completed_at": datetime.now()
                                })
                                
                                running_simulations[str(simulation_id)].update({
                                    "status": "completed",
                                    "progress": 100,
                                    "result": cached_simulation_result
                                })
                                
                                logger.info(f"Simulation {simulation_id} completed using cached result")
                                return
                            else:
                                logger.info("No cached simulation result found, will run simulation with cached intelligence")
                                # 有缓存的情报数据但没有推演结果，继续使用缓存的数据执行推演
                                # 不要return，让代码继续执行到后面的推演逻辑
                                
                                # 使用缓存的预识别数据
                                pre_identified_entities = cached.pre_identified_entities or []
                                pre_identified_relationships = cached.pre_identified_relationships or []
                                expanded_queries = cached.expanded_queries or []
                                
                                # 更新任务状态
                                intelligence_tasks[str(simulation_id)].update({
                                    "progress": 15,
                                    "pre_identified_entities": pre_identified_entities,
                                    "pre_identified_relationships": pre_identified_relationships,
                                    "expanded_queries": expanded_queries
                                })
                                
                                running_simulations[str(simulation_id)]["progress"] = 15
                                
                                # 跳过收集阶段，直接使用缓存的报告继续执行推演
                                # 更新状态为Agent构建
                                intelligence_tasks[str(simulation_id)]["status"] = "completed"
                                intelligence_tasks[str(simulation_id)]["progress"] = 100
                                intelligence_tasks[str(simulation_id)]["report"] = {
                                    "identified_entities": cached.identified_entities or []
                                }
                                intelligence_tasks[str(simulation_id)]["raw_contents"] = cached.collected_articles or []
                                
                                running_simulations[str(simulation_id)]["status"] = "building_agents"
                                running_simulations[str(simulation_id)]["progress"] = 40
                                
                                # 继续执行推演（跳过下面的收集代码）
                                logger.info("Continuing to simulation phase with cached intelligence...")
                                
                                # 继续执行推演
                                result = await orchestrator.run_simulation(event_description)
                                
                                # 将Pydantic模型序列化为字典，确保前端能正确解析
                                # mode='json' converts UUIDs and other types to JSON-serializable formats
                                result_dict = result.model_dump(mode='json') if result else None
                                
                                completed_data = {
                                    "status": "completed",
                                    "progress": 100,
                                    "result": result_dict,
                                    "completed_at": datetime.now()
                                }
                                await task_storage.update_task("simulation", str(simulation_id), completed_data)
                                running_simulations[str(simulation_id)].update(completed_data)
                                logger.info(f"Simulation {simulation_id} completed with {len(result_dict.get('paths', [])) if result_dict else 0} paths")
                                
                                # 推演成功后才保存到历史缓存
                                try:
                                    async with AsyncSessionLocal() as db:
                                        cache_service = IntelligenceCacheService(db)
                                        logger.info(f"Saving simulation result with {len(result_dict.get('paths', [])) if result_dict else 0} paths")
                                        # 只更新推演结果，保留缓存中已有的其他数据
                                        await cache_service.save_cache(
                                            event_description=event_description,
                                            simulation_result=result_dict
                                        )
                                        logger.info("Saved completed simulation to cache successfully")
                                except Exception as cache_error:
                                    logger.error(f"Failed to save cache: {cache_error}", exc_info=True)
                                
                                return
                        
                        # 如果需要增量更新，继续执行收集
                        logger.info("Cache needs update, proceeding with incremental collection")
                    else:
                        logger.info(f"No cache found for: {event_description[:50]}...")
                        
                        # Step 1: 进行查询扩展和实体预识别（LLM 调用）
                        query_expander = QueryExpander()
                        expansion_result = await query_expander.expand_query(event_description)
                        
                        # 准备预识别数据
                        pre_identified_entities = [
                            {
                                "name": e.name,
                                "entity_type": e.entity_type,
                                "role": e.role,
                                "relevance": e.relevance,
                                "rationale": e.rationale,
                                "key_interests": e.key_interests
                            }
                            for e in expansion_result.pre_identified_entities
                        ]
                        pre_identified_relationships = expansion_result.relationships if hasattr(expansion_result, 'relationships') else []
                        expanded_queries = [
                            {
                                "query": q.query,
                                "query_type": q.query_type,
                                "rationale": q.rationale,
                                "priority": q.priority
                            }
                            for q in expansion_result.expanded_queries
                        ]
                        
                        intelligence_tasks[str(simulation_id)].update({
                            "progress": 15,
                            "pre_identified_entities": pre_identified_entities,
                            "pre_identified_relationships": pre_identified_relationships,
                            "expanded_queries": expanded_queries
                        })
                        
                        running_simulations[str(simulation_id)]["progress"] = 15
                        
                        # 保存预识别结果到任务状态（不保存到历史缓存，等推演完成后再保存）
                        logger.info("Pre-identified entities ready for simulation")
                
                # Step 2: 执行完整的情报收集
                intelligence_tasks[str(simulation_id)]["progress"] = 30
                
                collector = IntelligenceCollector()
                collector.pre_identified_entities = pre_identified_entities
                collector.pre_identified_relationships = pre_identified_relationships
                
                # 使用数据库会话执行收集（启用缓存）
                async with AsyncSessionLocal() as db:
                    report = await collector.collect(event_description, use_cache=True, db=db)
                
                # 保存情报收集结果
                intelligence_tasks[str(simulation_id)].update({
                    "status": "completed",
                    "progress": 100,
                    "report": {
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
                        ]
                    },
                    "raw_contents": [
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
                        for content in collector.last_raw_contents[:20]
                    ] if hasattr(collector, 'last_raw_contents') else [],
                    "completed_at": datetime.now()
                })
                
                await collector.close()
                
                # 更新推演状态为Agent构建
                building_data = {"status": "building_agents", "progress": 40}
                await task_storage.update_task("simulation", str(simulation_id), building_data)
                running_simulations[str(simulation_id)].update(building_data)
                
                # 继续执行推演
                result = await orchestrator.run_simulation(event_description)
                
                # 将Pydantic模型序列化为字典，确保前端能正确解析
                # mode='json' converts UUIDs and other types to JSON-serializable formats
                result_dict = result.model_dump(mode='json') if result else None
                
                completed_data = {
                    "status": "completed",
                    "progress": 100,
                    "result": result_dict,
                    "completed_at": datetime.now()
                }
                await task_storage.update_task("simulation", str(simulation_id), completed_data)
                running_simulations[str(simulation_id)].update(completed_data)
                logger.info(f"Simulation {simulation_id} completed")
                
                # 输出详细的推演结果到日志
                if result_dict:
                    logger.info("=" * 60)
                    logger.info("SIMULATION RESULT DETAILS:")
                    logger.info(f"  - Simulation ID: {result_dict.get('simulation_id')}")
                    logger.info(f"  - Event ID: {result_dict.get('event_id')}")
                    logger.info(f"  - Participating Agents: {result_dict.get('participating_agents', [])}")
                    logger.info(f"  - Number of Rounds: {len(result_dict.get('rounds', []))}")
                    
                    # 输出每轮的详细信息
                    for i, round_data in enumerate(result_dict.get('rounds', [])):
                        logger.info(f"  - Round {i+1}: {len(round_data.get('actions', []))} actions")
                        for j, action in enumerate(round_data.get('actions', [])):
                            logger.info(f"    Action {j+1}: {action.get('agent_name')} - {action.get('action', {}).get('content', 'N/A')}")
                    
                    # 输出路径信息
                    paths = result_dict.get('paths', [])
                    logger.info(f"  - Number of Paths: {len(paths)}")
                    for i, path in enumerate(paths):
                        logger.info(f"    Path {i+1}: {path.get('name')} - {len(path.get('nodes', []))} nodes, {len(path.get('edges', []))} edges")
                        for j, node in enumerate(path.get('nodes', [])):
                            logger.info(f"      Node {j+1}: {node.get('entity')} - {node.get('action')}")
                    
                    logger.info("=" * 60)
                
                # 推演成功后才保存到历史缓存
                try:
                    async with AsyncSessionLocal() as db:
                        cache_service = IntelligenceCacheService(db)
                        logger.info(f"Saving simulation result with {len(result_dict.get('paths', [])) if result_dict else 0} paths")
                        # 只更新推演结果，保留缓存中已有的其他数据（由collector.collect()保存）
                        await cache_service.save_cache(
                            event_description=event_description,
                            simulation_result=result_dict
                        )
                        logger.info("Saved completed simulation to cache successfully")
                except Exception as cache_error:
                    logger.error(f"Failed to save cache: {cache_error}", exc_info=True)
                
            except Exception as e:
                logger.error(f"Simulation failed: {e}", exc_info=True)
                error_data = {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now()
                }
                await task_storage.update_task("simulation", str(simulation_id), error_data)
                running_simulations[str(simulation_id)].update(error_data)
                intelligence_tasks[str(simulation_id)].update(error_data)

        # 启动后台任务
        background_tasks.add_task(run_background)

        # 返回真实的任务ID
        return SimulationResponse(
            id=simulation_id,
            event_id=event_id,
            status="running",
            config=config,
            created_at="2026-03-10T10:00:00"
        )
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{simulation_id}")
async def get_simulation_status(simulation_id: str):
    """
    获取推演状态或结果

    如果推演完成，返回完整结果；否则返回当前状态
    """
    # 优先从Redis获取
    sim_data = await task_storage.get_task("simulation", simulation_id)

    # 如果Redis没有，尝试从内存获取
    if sim_data is None and simulation_id in running_simulations:
        sim_data = running_simulations[simulation_id]

    if sim_data is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Handle created_at - could be datetime object or ISO format string from Redis
    created_at = sim_data.get("created_at")
    if created_at:
        if isinstance(created_at, str):
            created_at_str = created_at
        else:
            created_at_str = created_at.isoformat()
    else:
        created_at_str = None

    response = {
        "id": simulation_id,
        "status": sim_data.get("status", "unknown"),
        "progress": sim_data.get("progress", 0),
        "message": "推演已完成" if sim_data["status"] == "completed" else "推演进行中",
        "created_at": created_at_str,
    }

    # 如果已完成，返回结果
    if sim_data["status"] == "completed" and sim_data.get("result"):
        response["result"] = sim_data["result"]

    # 如果失败，返回错误
    if sim_data["status"] == "failed":
        response["error"] = sim_data.get("error", "Unknown error")
        response["message"] = "推演失败"

    # 添加实体和关系数据（从情报任务或缓存中获取）
    event_description = sim_data.get("event_description", "")
    if event_description:
        try:
            from app.db.session import AsyncSessionLocal
            from app.services.intelligence.cache_service import IntelligenceCacheService

            async with AsyncSessionLocal() as db:
                cache_service = IntelligenceCacheService(db)
                cache = await cache_service.get_cache(event_description, max_age_hours=168)  # 7天内缓存

                if cache:
                    # 添加识别的实体
                    if cache.identified_entities:
                        response["identified_entities"] = cache.identified_entities

                    # 添加关系动态
                    if cache.relationship_dynamics:
                        response["relationship_dynamics"] = cache.relationship_dynamics
        except Exception as e:
            logger.warning(f"Failed to get cache data for simulation {simulation_id}: {e}")

    return response


@router.get("/", response_model=SimulationList)
async def list_simulations(
    page: int = 1,
    page_size: int = 20
):
    """获取推演列表"""
    return SimulationList(
        items=[],
        total=0,
        page=page,
        page_size=page_size
    )
