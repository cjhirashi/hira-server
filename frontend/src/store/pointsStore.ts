import { create } from 'zustand'

export interface PointValue {
  id: number
  name: string
  value: number | null
  unit: string | null
  quality: 'good' | 'uncertain' | 'bad'
  timestamp: string
}

interface PointsState {
  points: Record<number, PointValue>
  updatePoint: (point: PointValue) => void
  clearPoints: () => void
}

export const usePointsStore = create<PointsState>((set) => ({
  points: {},
  updatePoint: (point) =>
    set((state) => ({
      points: { ...state.points, [point.id]: point },
    })),
  clearPoints: () => set({ points: {} }),
}))
