// 实体类型
export interface Entity {
  id: string
  name: string
  name_en?: string
  entity_type: 'sovereign_state' | 'state_alliance' | 'international_org' | 'non_state_armed' | 'multinational_corp' | 'regional_power'
  description?: string
  attributes: EntityAttributes
  core_interests: string[]
  relationships: EntityRelationships
  agent_config: AgentConfig
  created_at: string
  updated_at?: string
}

export interface EntityAttributes {
  economic_power?: number
  military_power?: number
  diplomatic_influence?: number
  domestic_stability?: number
  strategic_patience?: number
  risk_tolerance?: number
  [key: string]: number | undefined
}

export interface EntityRelationships {
  allies: string[]
  adversaries: string[]
  complex: string[]
}

export interface AgentConfig {
  decision_style: string
  communication_style: string
  priority_dimensions: string[]
}

// 事件类型
export interface Event {
  id: string
  title: string
  description?: string
  event_date?: string
  reported_date?: string
  location?: Location
  primary_actor_id?: string
  target_id?: string
  involved_entities: string[]
  event_type?: string
  intensity?: number
  dimension_impacts: DimensionImpact
  sources: EventSource[]
}

export interface Location {
  country?: string
  region?: string
  city?: string
  coordinates?: { lat: number; lng: number }
}

export interface DimensionImpact {
  economic: number
  military: number
  diplomatic: number
  public_opinion: number
}

export interface EventSource {
  name: string
  url?: string
  published_at?: string
  reliability: number
}

// 推演类型
export interface Simulation {
  id: string
  event_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  config: SimulationConfig
  results?: SimulationResult
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface SimulationConfig {
  scenarios?: string[]
  time_horizons?: string[]
  dimensions?: string[]
  max_rounds?: number
}

export interface SimulationResult {
  simulation_id: string
  event_id: string
  participating_agents: string[]
  rounds: RoundResult[]
  paths: SimulationPath[]
  red_team_challenges: RedTeamChallenge[]
  synthesis: Synthesis
}

export interface RoundResult {
  round_number: number
  actions: AgentAction[]
  interactions: Interaction[]
  summary: string
}

export interface AgentAction {
  agent_id: string
  agent_name: string
  action: Action
  rationale: string
  confidence: number
}

export interface Action {
  type: string
  target?: string
  content: string
  intensity: number
  expected_outcome: string
}

export interface Interaction {
  type: string
  participants: string[]
  content: string
  outcome?: string
}

export interface SimulationPath {
  id: string
  name: string
  assumption: string
  probability: number
  confidence: string
  timeline: {
    short: TimelineNode[]
    medium: TimelineNode[]
    long: TimelineNode[]
  }
}

export interface TimelineNode {
  id: string
  event: string
  actor: string
  action: string
  timeframe: string
  description: string
  prerequisites: string[]
  consequences: string[]
}

export interface RedTeamChallenge {
  target_path: string
  challenge: string
  alternative_scenario?: string
  key_assumption_questioned: string
}

export interface Synthesis {
  key_uncertainties: KeyUncertainty[]
  early_warning_indicators: EarlyWarningIndicator[]
  overall_assessment: string
  strategic_implications: string[]
}

export interface KeyUncertainty {
  factor: string
  impact: string
  possible_outcomes: string[]
}

export interface EarlyWarningIndicator {
  indicator: string
  significance: string
  monitoring_source?: string
}


