import { create } from 'zustand'
import { Simulation, SimulationResult } from '../types'
import type { 
  NodeExecutionState, 
  RoundVisualization, 
  ExecutionEvent,
  NodeName,
  VisualizationMode 
} from '../types/simulation'

interface SimulationState {
  // 当前推演
  currentSimulation: Simulation | null
  simulationResult: SimulationResult | null
  loading: boolean
  error: string | null
  
  // 可视化状态
  nodeExecutionHistory: NodeExecutionState[]
  roundHistory: RoundVisualization[]
  currentNode: NodeName | null
  currentRound: number | null
  visualizationMode: VisualizationMode
  isReceivingEvents: boolean
  simulationStartTime: number | null
  simulationEndTime: number | null
  
  // 方法
  setCurrentSimulation: (simulation: Simulation | null) => void
  setSimulationResult: (result: SimulationResult | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // 可视化方法
  addNodeExecution: (nodeState: NodeExecutionState) => void
  updateNodeExecution: (nodeName: NodeName, updates: Partial<NodeExecutionState>) => void
  addRound: (round: RoundVisualization) => void
  updateRound: (roundNumber: number, updates: Partial<RoundVisualization>) => void
  addEntityDecision: (roundNumber: number, decision: any) => void
  setCurrentNode: (node: NodeName | null) => void
  setCurrentRound: (round: number | null) => void
  setVisualizationMode: (mode: VisualizationMode) => void
  setIsReceivingEvents: (isReceiving: boolean) => void
  setSimulationStartTime: (time: number | null) => void
  setSimulationEndTime: (time: number | null) => void
  processExecutionEvent: (event: ExecutionEvent) => void
  reset: () => void
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  currentSimulation: null,
  simulationResult: null,
  loading: false,
  error: null,
  
  // 可视化状态初始化
  nodeExecutionHistory: [],
  roundHistory: [],
  currentNode: null,
  currentRound: null,
  visualizationMode: 'realtime',
  isReceivingEvents: false,
  simulationStartTime: null,
  simulationEndTime: null,
  
  setCurrentSimulation: (simulation) => set({ currentSimulation: simulation }),
  setSimulationResult: (result) => set({ simulationResult: result }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  // 可视化方法实现
  addNodeExecution: (nodeState) => set((state) => ({
    nodeExecutionHistory: [...state.nodeExecutionHistory, nodeState]
  })),
  
  updateNodeExecution: (nodeName, updates) => set((state) => ({
    nodeExecutionHistory: state.nodeExecutionHistory.map(node =>
      node.nodeName === nodeName ? { ...node, ...updates } : node
    )
  })),
  
  addRound: (round) => set((state) => ({
    roundHistory: [...state.roundHistory, round]
  })),
  
  updateRound: (roundNumber, updates) => set((state) => ({
    roundHistory: state.roundHistory.map(round =>
      round.roundNumber === roundNumber ? { ...round, ...updates } : round
    )
  })),
  
  addEntityDecision: (roundNumber, decision) => set((state) => ({
    roundHistory: state.roundHistory.map(round =>
      round.roundNumber === roundNumber 
        ? { ...round, decisions: [...round.decisions, decision] }
        : round
    )
  })),
  
  setCurrentNode: (node) => set({ currentNode: node }),
  setCurrentRound: (round) => set({ currentRound: round }),
  setVisualizationMode: (mode) => set({ visualizationMode: mode }),
  setIsReceivingEvents: (isReceiving) => set({ isReceivingEvents: isReceiving }),
  setSimulationStartTime: (time) => set({ simulationStartTime: time }),
  setSimulationEndTime: (time) => set({ simulationEndTime: time }),
  
  // 处理执行事件
  processExecutionEvent: (event) => {
    const { event_type, node_name, timestamp, data } = event
    const currentTime = timestamp || Date.now()
    
    switch (event_type) {
      case 'simulation_started':
        set({
          simulationStartTime: currentTime,
          isReceivingEvents: true,
          nodeExecutionHistory: [],
          roundHistory: []
        })
        break
        
      case 'simulation_completed':
      case 'simulation_error':
        set({
          simulationEndTime: currentTime,
          isReceivingEvents: false
        })
        break
        
      case 'node_started':
        if (node_name) {
          const newNode: NodeExecutionState = {
            nodeName: node_name as NodeName,
            status: 'running',
            startTime: currentTime,
            data
          }
          get().addNodeExecution(newNode)
          set({ currentNode: node_name as NodeName })
        }
        break
        
      case 'node_completed':
        if (node_name) {
          get().updateNodeExecution(node_name as NodeName, {
            status: 'completed',
            endTime: currentTime,
            duration: currentTime - (get().nodeExecutionHistory.find(n => n.nodeName === node_name)?.startTime || currentTime),
            data
          })
        }
        break
        
      case 'node_error':
        if (node_name) {
          get().updateNodeExecution(node_name as NodeName, {
            status: 'error',
            endTime: currentTime,
            error: data?.error
          })
        }
        break
        
      case 'round_event':
        if (data?.round_number) {
          const roundNumber = data.round_number
          const existingRound = get().roundHistory.find(r => r.roundNumber === roundNumber)
          
          if (!existingRound && data.event_type === 'entity_decision_started') {
            // Create new round
            get().addRound({
              roundNumber,
              status: 'running',
              decisions: [],
              startTime: currentTime
            })
            set({ currentRound: roundNumber })
          } else if (existingRound) {
            // Update existing round
            if (data.event_type === 'entity_decision_completed' && data.decision) {
              get().addEntityDecision(roundNumber, {
                entityName: data.entity_name,
                actionType: data.decision.action_type,
                actionContent: data.decision.action_content,
                confidence: data.decision.confidence,
                status: 'decided'
              })
            } else if (data.situation_update) {
              get().updateRound(roundNumber, {
                situationSummary: data.situation_update,
                status: 'completed',
                endTime: currentTime
              })
            }
          }
        }
        break
    }
  },
  
  reset: () => set({
    currentSimulation: null,
    simulationResult: null,
    loading: false,
    error: null,
    nodeExecutionHistory: [],
    roundHistory: [],
    currentNode: null,
    currentRound: null,
    visualizationMode: 'realtime',
    isReceivingEvents: false,
    simulationStartTime: null,
    simulationEndTime: null
  })
}))
