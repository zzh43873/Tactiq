"""
推演相关Schema
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


class SimulationStatus(str, Enum):
    """推演状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TimeHorizon(str, Enum):
    """时间尺度"""
    SHORT = "short"    # 1-3个月
    MEDIUM = "medium"  # 6-12个月
    LONG = "long"      # 1-3年


class Dimension(str, Enum):
    """分析维度"""
    ECONOMIC = "economic"
    MILITARY = "military"
    DIPLOMATIC = "diplomatic"
    PUBLIC_OPINION = "public_opinion"


class ScenarioType(str, Enum):
    """情景类型"""
    COOPERATIVE = "cooperative"      # 合作路径
    CONFRONTATIONAL = "confrontational"  # 对抗路径
    MIXED = "mixed"                  # 混合路径


class SimulationConfig(BaseModel):
    """推演配置"""
    scenarios: List[ScenarioType] = Field(
        default=[ScenarioType.COOPERATIVE, ScenarioType.CONFRONTATIONAL, ScenarioType.MIXED]
    )
    time_horizons: List[TimeHorizon] = Field(
        default=[TimeHorizon.SHORT, TimeHorizon.MEDIUM, TimeHorizon.LONG]
    )
    dimensions: List[Dimension] = Field(
        default=[Dimension.ECONOMIC, Dimension.MILITARY, Dimension.DIPLOMATIC, Dimension.PUBLIC_OPINION]
    )
    max_rounds: int = Field(default=5, ge=1, le=10)


class SimulationRequest(BaseModel):
    """推演请求"""
    event_id: UUID = Field(..., description="事件ID")
    participating_entities: List[UUID] = Field(..., description="参与推演的实体")
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class Action(BaseModel):
    """行动定义"""
    type: str = Field(..., description="行动类型")
    target: Optional[str] = Field(default=None, description="目标")
    content: str = Field(..., description="行动内容")
    intensity: float = Field(..., ge=0.0, le=1.0, description="强度")
    expected_outcome: str = Field(..., description="预期结果")


class AgentAction(BaseModel):
    """Agent行动"""
    agent_id: str
    agent_name: str
    action: Action
    rationale: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class Interaction(BaseModel):
    """Agent间交互"""
    type: str = Field(..., description="交互类型: bilateral, multilateral, public")
    participants: List[str]
    content: str
    outcome: Optional[str] = None


class RoundResult(BaseModel):
    """单轮推演结果"""
    round_number: int
    actions: List[AgentAction]
    interactions: List[Interaction]
    summary: str


class TimelineNode(BaseModel):
    """时间线节点"""
    id: str
    event: str
    actor: str
    action: str
    timeframe: str
    description: str
    prerequisites: List[str] = Field(default=[])
    consequences: List[str] = Field(default=[])
    dimension_effects: Dict[str, str] = Field(default={})


class CausalNode(BaseModel):
    """因果图谱节点"""
    id: str
    entity: str
    entity_type: str
    action: str
    dimension: str = Field(..., description="military/economic/diplomatic/public_opinion")
    timeframe: str = Field(..., description="short/medium/long")
    description: str
    impact: float = Field(..., ge=0.0, le=1.0)
    location: Optional[Dict[str, Any]] = Field(default=None, description="地理位置 {lat, lng, name}")
    round_number: int = Field(default=1)


class CausalEdge(BaseModel):
    """因果图谱边"""
    source: str
    target: str
    label: Optional[str] = Field(default=None)
    type: str = Field(default="causal", description="causal/reactive/influence")
    strength: float = Field(default=0.5, ge=0.0, le=1.0)


class SimulationPath(BaseModel):
    """推演路径"""
    id: str
    name: str
    assumption: str
    probability: float = Field(..., ge=0.0, le=1.0)
    confidence: str = Field(..., description="high/medium/low")
    timeline: Dict[str, List[TimelineNode]] = Field(
        default={},
        description="short/medium/long时间线"
    )
    # 新增因果图谱数据
    nodes: List[CausalNode] = Field(default=[], description="因果节点列表")
    edges: List[CausalEdge] = Field(default=[], description="因果关系边列表")


class RedTeamChallenge(BaseModel):
    """红队挑战"""
    target_path: str
    challenge: str
    alternative_scenario: Optional[str] = None
    key_assumption_questioned: str


class KeyUncertainty(BaseModel):
    """关键不确定性"""
    factor: str
    impact: str
    possible_outcomes: List[str]


class EarlyWarningIndicator(BaseModel):
    """早期预警指标"""
    indicator: str
    significance: str
    monitoring_source: Optional[str] = None


class Synthesis(BaseModel):
    """综合评估"""
    key_uncertainties: List[KeyUncertainty]
    early_warning_indicators: List[EarlyWarningIndicator]
    overall_assessment: str
    strategic_implications: List[str]


class SimulationResult(BaseModel):
    """推演结果"""
    simulation_id: UUID
    event_id: UUID
    participating_agents: List[str]
    rounds: List[RoundResult]
    paths: List[SimulationPath]
    red_team_challenges: List[RedTeamChallenge]
    synthesis: Synthesis


class SimulationResponse(BaseModel):
    """推演响应"""
    id: UUID
    event_id: UUID
    status: SimulationStatus
    config: SimulationConfig
    results: Optional[SimulationResult] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SimulationList(BaseModel):
    """推演列表"""
    items: List[SimulationResponse]
    total: int
    page: int
    page_size: int
