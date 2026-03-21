import { create } from 'zustand'
import { Simulation, SimulationResult } from '../types'

interface SimulationState {
  // 当前推演
  currentSimulation: Simulation | null
  simulationResult: SimulationResult | null
  loading: boolean
  error: string | null
  
  // 方法
  setCurrentSimulation: (simulation: Simulation | null) => void
  setSimulationResult: (result: SimulationResult | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

export const useSimulationStore = create<SimulationState>((set) => ({
  currentSimulation: null,
  simulationResult: null,
  loading: false,
  error: null,
  
  setCurrentSimulation: (simulation) => set({ currentSimulation: simulation }),
  setSimulationResult: (result) => set({ simulationResult: result }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({
    currentSimulation: null,
    simulationResult: null,
    loading: false,
    error: null
  })
}))
