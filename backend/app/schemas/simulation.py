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
    max_rounds: int = Field(default=3, ge=1, le=10)
    max_entities: int = Field(default=12, ge=1, le=20, description="Maximum number of entities to identify")


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


# ── New entity-game schemas ───────────────────────────────────────────────────

class GeopoliticalInput(BaseModel):
    """Input schema for the new entity-game simulation pipeline."""
    proposition: str = Field(
        ...,
        description="地缘政治命题，可以是一条现有政策、新闻事件或假设性情景",
        examples=[u"特朗普宣布出动地面部队攻击伊朗"]
    )
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class EntityReactionSchema(BaseModel):
    """An entity's predicted reaction across multiple dimensions."""
    military: str = Field(default="", description="军事行动预测")
    diplomatic: str = Field(default="", description="外交反应预测")
    economic: str = Field(default="", description="经济措施预测")
    energy: str = Field(default="", description="能源/资源相关反应")
    public_opinion: str = Field(default="", description="舆论/媒体策略")
    rationale: str = Field(default="", description="决策依据")
    confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="置信度")


class EntityInfo(BaseModel):
    """A geopolitical entity identified from the proposition."""
    name: str
    name_en: str = ""
    entity_type: str = Field(default="country", description="country/non_state_actor/organization/market")
    role: str = Field(default="stakeholder", description="initiator/target/ally/adversary/stakeholder/proxy")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    initial_stance: str = ""


class SimulationRoundResult(BaseModel):
    """Results of one round of parallel entity decisions."""
    round_number: int
    global_summary: str = ""
    entity_reactions: Dict[str, EntityReactionSchema] = Field(default_factory=dict)


class FinalReportSchema(BaseModel):
    """Comprehensive final output of the entity-game simulation."""
    entities: Dict[str, EntityReactionSchema] = Field(
        default_factory=dict,
        description="Per-entity consolidated reactions"
    )
    key_turning_points: List[str] = Field(default_factory=list)
    escalation_risk: float = Field(default=0.5, ge=0.0, le=1.0)
    most_likely_scenario: str = ""
    alternative_scenarios: List[str] = Field(default_factory=list)
    timeline: Dict[str, List[str]] = Field(
        default_factory=lambda: {"short": [], "medium": [], "long": []}
    )
    early_warning_indicators: List[str] = Field(default_factory=list)


class GeopoliticalSimulationResult(BaseModel):
    """Full result of the entity-game simulation pipeline."""
    proposition: str
    entities_identified: List[EntityInfo] = Field(default_factory=list)
    simulation_rounds: List[SimulationRoundResult] = Field(default_factory=list)
    final_report: FinalReportSchema = Field(default_factory=FinalReportSchema)
