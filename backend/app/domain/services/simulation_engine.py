"""
推演引擎 - 核心领域服务

使用 LangGraph 编排多轮推演流程
"""
import json
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from loguru import logger
from langgraph.graph import StateGraph, END, START

from app.domain.entities import GeopoliticalEntity
from app.domain.services.decision_engine import DecisionEngine, DebateContext, DecisionResult
from app.infrastructure.external.llm import LLMProvider, Message


class SimulationStatus(str, Enum):
    """推演状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RoundResult:
    """单轮推演结果"""
    round_number: int
    decisions: List[DecisionResult]
    situation_summary: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SimulationResult:
    """推演结果"""
    simulation_id: str
    proposition: str
    status: SimulationStatus
    entities: List[GeopoliticalEntity]
    rounds: List[RoundResult]
    final_report: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# LangGraph 状态定义
class SimulationState(TypedDict):
    """推演状态"""
    proposition: str
    entities: List[Dict[str, Any]]
    current_round: int
    max_rounds: int
    round_results: List[Dict[str, Any]]
    situation_summary: str
    is_complete: bool
    final_report: Optional[str]
    error: Optional[str]


class SimulationEngine:
    """
    推演引擎
    
    使用 LangGraph 编排四阶段推演流程：
    1. Entity Identification - 实体识别
    2. Entity Profiling - 实体画像
    3. Game Coordination - 博弈推演（多轮）
    4. Synthesis - 综合报告
    """
    
    def __init__(self, llm_provider: LLMProvider, event_callback: Optional[callable] = None):
        self._llm = llm_provider
        self._decision_engine = DecisionEngine(llm_provider)
        self._event_callback = event_callback
        self._graph = self._build_graph()
        self._simulation_id: Optional[str] = None
    
    def set_simulation_id(self, simulation_id: str):
        """设置当前推演ID，用于事件发布"""
        self._simulation_id = simulation_id
    
    async def _emit_event(self, event_type: str, node_name: str, data: dict = None):
        """发射节点执行事件"""
        if self._event_callback and self._simulation_id:
            try:
                await self._event_callback(
                    "simulation",
                    self._simulation_id,
                    event_type,
                    node_name,
                    data
                )
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")
    
    def _build_graph(self):
        """构建 LangGraph 状态图"""
        workflow = StateGraph(SimulationState)
        
        # 添加节点
        workflow.add_node("identify_entities", self._identify_entities)
        workflow.add_node("profile_entities", self._profile_entities)
        workflow.add_node("coordinate_game", self._coordinate_game)
        workflow.add_node("check_completion", self._check_completion)
        workflow.add_node("synthesize", self._synthesize)
        
        # 设置入口点 - LangGraph 1.x 标准写法
        workflow.add_edge(START, "identify_entities")
        
        # 添加边
        workflow.add_edge("identify_entities", "profile_entities")
        workflow.add_edge("profile_entities", "coordinate_game")
        workflow.add_edge("coordinate_game", "check_completion")
        
        # 条件边
        workflow.add_conditional_edges(
            "check_completion",
            self._should_continue,
            {
                "continue": "coordinate_game",
                "complete": "synthesize"
            }
        )
        
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    async def run_simulation(
        self,
        simulation_id: str,
        proposition: str,
        entities: Optional[List[GeopoliticalEntity]] = None,
        max_rounds: int = 3
    ) -> SimulationResult:
        """
        运行推演
        
        Args:
            simulation_id: 推演ID
            proposition: 推演命题
            entities: 预识别的实体列表（可选）
            max_rounds: 最大推演轮数
        """
        # 设置推演ID用于事件发布
        self.set_simulation_id(simulation_id)
        
        # 初始化状态
        initial_state: SimulationState = {
            "proposition": proposition,
            "entities": [self._entity_to_dict(e) for e in (entities or [])],
            "current_round": 0,
            "max_rounds": max_rounds,
            "round_results": [],
            "situation_summary": f"推演开始：{proposition}",
            "is_complete": False,
            "final_report": None,
            "error": None
        }
        
        try:
            # 发送推演开始事件
            logger.info(f"[SimulationEngine] 开始推演: {simulation_id}")
            await self._emit_event("simulation_started", "run_simulation", {
                "simulation_id": simulation_id,
                "proposition": proposition,
                "max_rounds": max_rounds,
                "entity_count": len(entities or [])
            })
            
            # 执行图
            logger.info("[SimulationEngine] 开始执行LangGraph...")
            final_state = await self._graph.ainvoke(initial_state)
            logger.info("[SimulationEngine] LangGraph执行完成")
            
            # 发送推演完成事件
            await self._emit_event("simulation_completed", "run_simulation", {
                "simulation_id": simulation_id,
                "status": "completed" if not final_state.get("error") else "failed",
                "rounds_completed": len(final_state.get("round_results", [])),
                "error": final_state.get("error")
            })
            
            # 构建结果
            return SimulationResult(
                simulation_id=simulation_id,
                proposition=proposition,
                status=SimulationStatus.COMPLETED if not final_state.get("error") else SimulationStatus.FAILED,
                entities=[self._dict_to_entity(e) for e in final_state.get("entities", [])],
                rounds=[self._dict_to_round(r) for r in final_state.get("round_results", [])],
                final_report=final_state.get("final_report"),
                error_message=final_state.get("error"),
                completed_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"[SimulationEngine] 推演执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 发送推演失败事件
            await self._emit_event("simulation_error", "run_simulation", {
                "simulation_id": simulation_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            
            return SimulationResult(
                simulation_id=simulation_id,
                proposition=proposition,
                status=SimulationStatus.FAILED,
                entities=entities or [],
                rounds=[],
                error_message=str(e),
                completed_at=datetime.now()
            )
    
    async def _identify_entities(self, state: SimulationState) -> SimulationState:
        """阶段1: 实体识别"""
        logger.info("[SimulationEngine] 开始实体识别节点")
        await self._emit_event("node_started", "identify_entities", {"proposition": state["proposition"]})
        
        if state["entities"]:
            # 如果已提供实体，跳过识别
            logger.info(f"[SimulationEngine] 实体识别跳过，已有 {len(state['entities'])} 个实体")
            await self._emit_event("node_completed", "identify_entities", {"skipped": True, "entity_count": len(state["entities"])})
            return state
        
        prompt = f"""分析以下地缘政治命题，识别所有相关实体（国家、组织、地区等）：

命题：{state['proposition']}

请以JSON格式输出实体列表：
{{
    "entities": [
        {{
            "name": "实体名称",
            "name_en": "英文名称",
            "entity_type": "sovereign_state|organization|region",
            "core_interests": ["核心利益1", "核心利益2"]
        }}
    ]
}}"""

        try:
            logger.info("[SimulationEngine] 调用LLM进行实体识别...")
            response = await self._llm.chat(
                messages=[Message(role="user", content=prompt)],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            logger.info(f"[SimulationEngine] LLM响应: {response.content[:200]}...")
            result = json.loads(response.content)
            state["entities"] = result.get("entities", [])
            state["situation_summary"] = f"识别到 {len(state['entities'])} 个实体"
            
            logger.info(f"[SimulationEngine] 实体识别完成，识别到 {len(state['entities'])} 个实体")
            await self._emit_event("node_completed", "identify_entities", {
                "entity_count": len(state["entities"]),
                "entities": [{"name": e.get("name"), "type": e.get("entity_type")} for e in state["entities"]]
            })
            
        except Exception as e:
            logger.error(f"[SimulationEngine] 实体识别失败: {e}")
            state["error"] = f"实体识别失败: {str(e)}"
            await self._emit_event("node_error", "identify_entities", {"error": str(e)})
        
        return state
    
    async def _profile_entities(self, state: SimulationState) -> SimulationState:
        """阶段2: 实体画像"""
        await self._emit_event("node_started", "profile_entities", {"entity_count": len(state.get("entities", []))})
        
        if state.get("error"):
            await self._emit_event("node_completed", "profile_entities", {"skipped": True, "error": state.get("error")})
            return state
        
        for entity_dict in state["entities"]:
            prompt = f"""为以下实体构建详细的政治画像：

实体：{entity_dict['name']}
类型：{entity_dict.get('entity_type', 'sovereign_state')}
核心利益：{entity_dict.get('core_interests', [])}

命题背景：{state['proposition']}

请分析该实体在此情境下的：
1. 政治立场和态度
2. 可动用的资源和能力
3. 可能的盟友和对手
4. 决策约束条件

以JSON格式输出。"""

            try:
                response = await self._llm.chat(
                    messages=[Message(role="user", content=prompt)],
                    temperature=0.5,
                    response_format={"type": "json_object"}
                )
                
                profile = json.loads(response.content)
                entity_dict["profile"] = profile
                
            except Exception:
                entity_dict["profile"] = {}
        
        state["situation_summary"] = f"已完成 {len(state['entities'])} 个实体的画像构建"
        await self._emit_event("node_completed", "profile_entities", {
            "entity_count": len(state["entities"]),
            "profiles_completed": len([e for e in state["entities"] if e.get("profile")])
        })
        return state
    
    async def _coordinate_game(self, state: SimulationState) -> SimulationState:
        """阶段3: 博弈推演 - 执行一轮推演"""
        state["current_round"] += 1
        round_number = state["current_round"]
        
        await self._emit_event("node_started", "coordinate_game", {
            "round_number": round_number,
            "max_rounds": state["max_rounds"]
        })
        
        if state.get("error"):
            await self._emit_event("node_completed", "coordinate_game", {"skipped": True, "error": state.get("error")})
            return state
        
        # 转换实体
        entities = [self._dict_to_entity(e) for e in state["entities"]]
        
        # 收集历史决策
        previous_decisions = []
        for round_result in state["round_results"]:
            previous_decisions.extend([
                self._dict_to_decision(d) 
                for d in round_result.get("decisions", [])
            ])
        
        # 为每个实体执行鹰鸽辩论决策
        round_decisions = []
        for idx, entity in enumerate(entities):
            await self._emit_event("round_event", "coordinate_game", {
                "round_number": round_number,
                "event_type": "entity_decision_started",
                "entity_name": entity.name,
                "progress": f"{idx + 1}/{len(entities)}"
            })
            
            context = DebateContext(
                proposition=state["proposition"],
                round_number=round_number,
                previous_decisions=previous_decisions,
                other_entities=[e for e in entities if e.name != entity.name],
                situation_summary=state["situation_summary"]
            )
            
            decision = await self._decision_engine.make_decision(entity, context)
            round_decisions.append(decision)
            
            await self._emit_event("round_event", "coordinate_game", {
                "round_number": round_number,
                "event_type": "entity_decision_completed",
                "entity_name": entity.name,
                "decision": {
                    "action_type": decision.action_type.value,
                    "action_content": decision.action_content,
                    "confidence": decision.confidence
                }
            })
        
        # 更新局势摘要
        situation_update = await self._update_situation(
            state["proposition"],
            state["situation_summary"],
            round_decisions
        )
        
        # 保存本轮结果
        round_result = {
            "round_number": round_number,
            "decisions": [self._decision_to_dict(d) for d in round_decisions],
            "situation_summary": situation_update,
            "timestamp": datetime.now().isoformat()
        }
        state["round_results"].append(round_result)
        state["situation_summary"] = situation_update
        
        await self._emit_event("node_completed", "coordinate_game", {
            "round_number": round_number,
            "decisions_count": len(round_decisions),
            "situation_update": situation_update
        })
        
        return state
    
    async def _check_completion(self, state: SimulationState) -> SimulationState:
        """检查推演是否完成"""
        await self._emit_event("node_started", "check_completion", {
            "current_round": state["current_round"],
            "max_rounds": state["max_rounds"]
        })
        
        if state.get("error"):
            state["is_complete"] = True
            await self._emit_event("node_completed", "check_completion", {"is_complete": True, "reason": "error"})
            return state
        
        # 检查是否达到最大轮数
        if state["current_round"] >= state["max_rounds"]:
            state["is_complete"] = True
            await self._emit_event("node_completed", "check_completion", {"is_complete": True, "reason": "max_rounds_reached"})
            return state
        
        # 检查是否达到稳态（可选）
        # TODO: 实现收敛检测逻辑
        
        await self._emit_event("node_completed", "check_completion", {"is_complete": False, "reason": "continue"})
        return state
    
    def _should_continue(self, state: SimulationState) -> str:
        """决定下一步"""
        if state.get("is_complete"):
            return "complete"
        return "continue"
    
    async def _synthesize(self, state: SimulationState) -> SimulationState:
        """阶段4: 综合报告生成"""
        await self._emit_event("node_started", "synthesize", {
            "round_count": len(state.get("round_results", [])),
            "entity_count": len(state.get("entities", []))
        })
        
        if state.get("error"):
            await self._emit_event("node_completed", "synthesize", {"skipped": True, "error": state.get("error")})
            return state
        
        prompt = f"""基于以下推演结果生成综合分析报告：

命题：{state['proposition']}

推演过程：
{json.dumps(state['round_results'], ensure_ascii=False, indent=2)}

请生成包含以下内容的报告：
1. 执行摘要
2. 各实体行为分析
3. 局势演变过程
4. 关键转折点
5. 风险评估
6. 政策建议

以Markdown格式输出。"""

        try:
            response = await self._llm.chat(
                messages=[Message(role="user", content=prompt)],
                temperature=0.7
            )
            
            state["final_report"] = response.content
            await self._emit_event("node_completed", "synthesize", {
                "report_length": len(response.content),
                "round_count": len(state["round_results"])
            })
            
        except Exception as e:
            state["final_report"] = f"报告生成失败: {str(e)}"
            await self._emit_event("node_error", "synthesize", {"error": str(e)})
        
        return state
    
    async def _update_situation(
        self,
        proposition: str,
        current_situation: str,
        decisions: List[DecisionResult]
    ) -> str:
        """更新局势摘要"""
        decisions_str = "\n".join([
            f"- {d.entity_name}: {d.action_content} (风险: {d.international_risk})"
            for d in decisions
        ])
        
        prompt = f"""基于最新决策更新局势摘要：

命题：{proposition}
当前局势：{current_situation}

最新决策：
{decisions_str}

请用2-3句话总结新的局势发展。"""

        try:
            response = await self._llm.chat(
                messages=[Message(role="user", content=prompt)],
                temperature=0.5
            )
            return response.content
        except Exception:
            return current_situation
    
    # 辅助方法：数据转换
    def _entity_to_dict(self, entity: GeopoliticalEntity) -> Dict[str, Any]:
        return {
            "name": entity.name,
            "name_en": entity.name_en,
            "entity_type": entity.entity_type.value,
            "role": entity.role.value,
            "relevance_score": entity.relevance_score,
            "core_interests": entity.core_interests,
            "capabilities": {
                "military_power": entity.capabilities.military_power,
                "economic_power": entity.capabilities.economic_power,
                "diplomatic_influence": entity.capabilities.diplomatic_influence,
                "domestic_stability": entity.capabilities.domestic_stability,
                "strategic_patience": entity.capabilities.strategic_patience,
                "risk_tolerance": entity.capabilities.risk_tolerance
            }
        }
    
    def _dict_to_entity(self, data: Dict[str, Any]) -> GeopoliticalEntity:
        from app.domain.entities import EntityType, EntityRole, EntityCapabilities
        
        caps = data.get("capabilities", {})
        return GeopoliticalEntity(
            name=data["name"],
            name_en=data.get("name_en"),
            entity_type=EntityType(data.get("entity_type", "sovereign_state")),
            role=EntityRole(data.get("role", "stakeholder")),
            relevance_score=data.get("relevance_score", 0.5),
            core_interests=data.get("core_interests", []),
            capabilities=EntityCapabilities(
                military_power=caps.get("military_power", 0.5),
                economic_power=caps.get("economic_power", 0.5),
                diplomatic_influence=caps.get("diplomatic_influence", 0.5),
                domestic_stability=caps.get("domestic_stability", 0.5),
                strategic_patience=caps.get("strategic_patience", 0.5),
                risk_tolerance=caps.get("risk_tolerance", 0.5)
            )
        )
    
    def _decision_to_dict(self, decision: DecisionResult) -> Dict[str, Any]:
        return {
            "entity_name": decision.entity_name,
            "action_type": decision.action_type.value,
            "action_content": decision.action_content,
            "target_entities": decision.target_entities,
            "reasoning": decision.reasoning,
            "confidence": decision.confidence,
            "domestic_cost": decision.domestic_cost,
            "international_risk": decision.international_risk,
            "expected_outcome": decision.expected_outcome
        }
    
    def _dict_to_decision(self, data: Dict[str, Any]) -> DecisionResult:
        from app.domain.services.decision_engine import ActionType
        
        return DecisionResult(
            entity_name=data["entity_name"],
            action_type=ActionType(data.get("action_type", "diplomatic")),
            action_content=data["action_content"],
            target_entities=data.get("target_entities", []),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.5),
            domestic_cost=data.get("domestic_cost", 0.5),
            international_risk=data.get("international_risk", 0.5),
            expected_outcome=data.get("expected_outcome", "")
        )
    
    def _dict_to_round(self, data: Dict[str, Any]) -> RoundResult:
        return RoundResult(
            round_number=data["round_number"],
            decisions=[self._dict_to_decision(d) for d in data.get("decisions", [])],
            situation_summary=data.get("situation_summary", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        )
