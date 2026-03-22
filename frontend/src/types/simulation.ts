/**
 * Simulation workflow visualization types
 */

// Node execution event types
export type NodeEventType = 
  | 'simulation_started'
  | 'simulation_completed'
  | 'simulation_error'
  | 'node_started'
  | 'node_completed'
  | 'node_error'
  | 'round_event';

// LangGraph node names
export type NodeName = 
  | 'identify_entities'
  | 'profile_entities'
  | 'coordinate_game'
  | 'check_completion'
  | 'synthesize'
  | 'run_simulation';

// Node execution state
export interface NodeExecutionState {
  nodeName: NodeName;
  status: 'pending' | 'running' | 'completed' | 'error';
  startTime?: number;
  endTime?: number;
  duration?: number;
  data?: any;
  error?: string;
}

// Execution event from WebSocket
export interface ExecutionEvent {
  type: 'node_event' | 'round_event' | 'progress' | 'status';
  event_type?: NodeEventType;
  node_name?: NodeName;
  timestamp?: number;
  data?: any;
}

// Round event data
export interface RoundEventData {
  round_number: number;
  event_type: 'entity_decision_started' | 'entity_decision_completed' | string;
  entity_name?: string;
  progress?: string;
  decision?: {
    action_type: string;
    action_content: string;
    confidence: number;
  };
}

// Round visualization data
export interface RoundVisualization {
  roundNumber: number;
  status: 'pending' | 'running' | 'completed';
  decisions: EntityDecision[];
  situationSummary?: string;
  startTime?: number;
  endTime?: number;
}

// Entity decision in a round
export interface EntityDecision {
  entityName: string;
  actionType: string;
  actionContent: string;
  confidence: number;
  reasoning?: string;
  domesticCost?: number;
  internationalRisk?: number;
  status: 'pending' | 'debating' | 'decided';
  // Hawk/Dove debate results
  debate?: {
    hawkArgument: string;
    doveArgument: string;
  };
}

// Workflow graph node for ReactFlow
export interface WorkflowNode {
  id: string;
  type: 'default' | 'input' | 'output' | 'group';
  position: { x: number; y: number };
  data: {
    label: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    startTime?: number;
    endTime?: number;
    details?: any;
  };
  style?: React.CSSProperties;
}

// Workflow graph edge for ReactFlow
export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: 'default' | 'straight' | 'step' | 'smoothstep';
  animated?: boolean;
  style?: React.CSSProperties;
  label?: string;
}

// Execution trace (complete history)
export interface ExecutionTrace {
  simulationId: string;
  proposition: string;
  startTime: number;
  endTime?: number;
  status: 'running' | 'completed' | 'error';
  nodes: NodeExecutionState[];
  rounds: RoundVisualization[];
  currentNode?: NodeName;
  currentRound?: number;
  error?: string;
}

// Timeline item for execution timeline
export interface TimelineItem {
  id: string;
  type: 'node' | 'round' | 'decision' | 'milestone';
  title: string;
  description?: string;
  timestamp: number;
  status: 'pending' | 'running' | 'completed' | 'error';
  duration?: number;
  details?: any;
  icon?: string;
}

// Visualization mode
export type VisualizationMode = 'realtime' | 'summary';

// Simulation store extended state
export interface SimulationVisualizationState {
  executionTrace: ExecutionTrace | null;
  currentNode: NodeName | null;
  currentRound: number | null;
  visualizationMode: VisualizationMode;
  nodeExecutionHistory: NodeExecutionState[];
  roundHistory: RoundVisualization[];
  isReceivingEvents: boolean;
}
