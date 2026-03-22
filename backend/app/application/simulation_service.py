"""
推演应用服务

协调推演流程，管理推演状态，发布领域事件
集成 LangGraph 推演引擎
"""
from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime
from loguru import logger

from app.domain.events import (
    event_bus,
    SimulationStarted,
    SimulationCompleted,
    RoundCompleted,
    EntityReacted,
)
from app.domain.services import SimulationEngine, SimulationResult, SimulationStatus, RoundResult
from app.infrastructure.repositories import SimulationRepository
from app.infrastructure.external.llm import LLMProvider
from app.models.simulation import SimulationStatus as ModelStatus
from app.api.v1.websocket import publish_node_event, publish_round_event


class SimulationApplicationService:
    """
    推演应用服务
    
    职责：
    1. 协调推演流程
    2. 管理推演状态
    3. 发布领域事件
    4. 处理推演结果持久化
    5. 集成 LangGraph 推演引擎
    """
    
    def __init__(
        self, 
        repository: SimulationRepository,
        llm_provider: Optional[LLMProvider] = None
    ):
        self._repository = repository
        # 创建事件回调函数
        async def event_callback(task_type, task_id, event_type, node_name, data):
            if event_type.startswith("round"):
                await publish_round_event(task_type, task_id, data.get("round_number", 0), event_type, data)
            else:
                await publish_node_event(task_type, task_id, event_type, node_name, data)
        
        self._engine = SimulationEngine(llm_provider, event_callback) if llm_provider else None
    
    async def start_simulation(
        self,
        proposition: str,
        config: Dict[str, Any] = None,
        event_id: Optional[str] = None,
        entities: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        启动推演
        
        Args:
            proposition: 推演命题
            config: 推演配置
            event_id: 关联事件ID
            entities: 预识别实体列表（可选）
            
        Returns:
            simulation_id: 推演ID
        """
        simulation_id = str(uuid4())
        
        # 创建推演记录
        await self._repository.add({
            "id": simulation_id,
            "event_id": event_id,
            "proposition": proposition,
            "config": config or {},
            "status": ModelStatus.RUNNING.value,
            "started_at": datetime.now(),
        })
        
        # 发布开始事件
        await event_bus.publish(
            SimulationStarted(
                simulation_id=simulation_id,
                proposition=proposition,
                config=config or {}
            )
        )
        
        logger.info(f"Started simulation: {simulation_id}")
        return simulation_id
    
    async def execute_simulation(
        self,
        simulation_id: str,
        proposition: str,
        config: Dict[str, Any] = None,
        entities: Optional[List[Dict[str, Any]]] = None
    ) -> SimulationResult:
        """
        执行推演（使用 LangGraph 引擎）
        
        Args:
            simulation_id: 推演ID
            proposition: 推演命题
            config: 推演配置
            entities: 预识别实体列表
            
        Returns:
            SimulationResult: 推演结果
        """
        if not self._engine:
            raise RuntimeError("Simulation engine not initialized. LLM provider required.")
        
        from app.domain.entities import GeopoliticalEntity, EntityType, EntityRole
        
        # 转换实体
        entity_objects = []
        if entities:
            for e in entities:
                entity_objects.append(GeopoliticalEntity(
                    name=e.get("name", "Unknown"),
                    name_en=e.get("name_en"),
                    entity_type=EntityType(e.get("entity_type", "sovereign_state")),
                    role=EntityRole(e.get("role", "stakeholder")),
                    relevance_score=e.get("relevance_score", 0.5),
                    core_interests=e.get("core_interests", [])
                ))
        
        # 执行推演
        max_rounds = config.get("max_rounds", 3) if config else 3
        
        result = await self._engine.run_simulation(
            simulation_id=simulation_id,
            proposition=proposition,
            entities=entity_objects if entity_objects else None,
            max_rounds=max_rounds
        )
        
        # 记录每轮结果
        for round_result in result.rounds:
            entity_reactions = {
                d.entity_name: {
                    "action_type": d.action_type.value,
                    "action_content": d.action_content,
                    "reasoning": d.reasoning,
                    "confidence": d.confidence
                }
                for d in round_result.decisions
            }
            
            await self.record_round_completion(
                simulation_id=simulation_id,
                round_number=round_result.round_number,
                entity_reactions=entity_reactions,
                global_summary=round_result.situation_summary
            )
        
        # 完成推演
        if result.status == SimulationStatus.COMPLETED:
            results_dict = {
                "entities_identified": [e.name for e in result.entities],
                "simulation_rounds": [
                    {
                        "round": r.round_number,
                        "decisions": [
                            {
                                "entity": d.entity_name,
                                "action": d.action_content,
                                "type": d.action_type.value,
                                "risk": d.international_risk
                            }
                            for d in r.decisions
                        ],
                        "summary": r.situation_summary
                    }
                    for r in result.rounds
                ],
                "final_report": result.final_report
            }
            
            await self.complete_simulation(
                simulation_id=simulation_id,
                results=results_dict
            )
        else:
            await self.fail_simulation(
                simulation_id=simulation_id,
                error_message=result.error_message or "Unknown error"
            )
        
        return result
    
    async def record_round_completion(
        self,
        simulation_id: str,
        round_number: int,
        entity_reactions: Dict[str, Dict[str, Any]],
        global_summary: str
    ) -> None:
        """
        记录轮次完成
        
        Args:
            simulation_id: 推演ID
            round_number: 轮次编号
            entity_reactions: 实体反应
            global_summary: 全局摘要
        """
        # 发布轮次完成事件
        await event_bus.publish(
            RoundCompleted(
                simulation_id=simulation_id,
                round_number=round_number,
                entity_reactions=entity_reactions,
                global_summary=global_summary
            )
        )
        
        # 发布每个实体的反应事件
        for entity_name, reaction in entity_reactions.items():
            await event_bus.publish(
                EntityReacted(
                    simulation_id=simulation_id,
                    entity_name=entity_name,
                    round_number=round_number,
                    reaction=reaction
                )
            )
        
        logger.debug(f"Recorded round {round_number} for simulation: {simulation_id}")
    
    async def complete_simulation(
        self,
        simulation_id: str,
        results: Dict[str, Any],
        duration_seconds: Optional[float] = None
    ) -> None:
        """
        完成推演
        
        Args:
            simulation_id: 推演ID
            results: 推演结果
            duration_seconds: 耗时（秒）
        """
        # 更新推演记录
        await self._repository.update({
            "id": simulation_id,
            "status": SimulationStatus.COMPLETED.value,
            "results": results,
            "completed_at": datetime.now(),
        })
        
        # 发布完成事件
        await event_bus.publish(
            SimulationCompleted(
                simulation_id=simulation_id,
                status="completed",
                result_summary={
                    "entities_count": len(results.get("entities_identified", [])),
                    "rounds_count": len(results.get("simulation_rounds", [])),
                    "escalation_risk": results.get("final_report", {}).get("escalation_risk"),
                },
                duration_seconds=duration_seconds
            )
        )
        
        logger.info(f"Completed simulation: {simulation_id}")
    
    async def fail_simulation(
        self,
        simulation_id: str,
        error_message: str
    ) -> None:
        """
        标记推演失败
        
        Args:
            simulation_id: 推演ID
            error_message: 错误信息
        """
        # 更新状态
        await self._repository.update_status(
            simulation_id,
            SimulationStatus.FAILED,
            error_message
        )
        
        # 发布完成事件（失败状态）
        await event_bus.publish(
            SimulationCompleted(
                simulation_id=simulation_id,
                status="failed",
                error_message=error_message
            )
        )
        
        logger.error(f"Simulation failed: {simulation_id}, error: {error_message}")
    
    async def get_simulation(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """获取推演记录"""
        return await self._repository.get_by_id(simulation_id)
    
    async def list_simulations(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出演算"""
        filters = {"limit": limit, "offset": offset}
        if status:
            filters["status"] = SimulationStatus(status)
        return await self._repository.list(**filters)
