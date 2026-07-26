import { usePointsStore } from '../../store/pointsStore'

export interface Binding {
  point_id: number
  true_when?: string
}

export interface BindingMap {
  [key: string]: Binding | boolean | undefined
}

function evalTrueWhen(expr: string, value: number | null): boolean {
  if (value === null) return false
  const v = value
  try {
    if (expr.includes('==')) {
      const [, rhs] = expr.split('==')
      return v === Number(rhs.trim())
    }
    if (expr.includes('!=')) {
      const [, rhs] = expr.split('!=')
      return v !== Number(rhs.trim())
    }
    if (expr.includes('>=')) {
      const [, rhs] = expr.split('>=')
      return v >= Number(rhs.trim())
    }
    if (expr.includes('>')) {
      const [, rhs] = expr.split('>')
      return v > Number(rhs.trim())
    }
    if (expr.includes('<=')) {
      const [, rhs] = expr.split('<=')
      return v <= Number(rhs.trim())
    }
  } catch {
    return false
  }
  return Boolean(v)
}

export function useBinding(binding: Binding | undefined): number | null {
  const points = usePointsStore((s) => s.points)
  if (!binding) return null
  const pt = points[binding.point_id]
  return pt?.value ?? null
}

export function useBoolBinding(binding: Binding | undefined): boolean {
  const points = usePointsStore((s) => s.points)
  if (!binding) return false
  const pt = points[binding.point_id]
  const value = pt?.value ?? null
  if (binding.true_when) return evalTrueWhen(binding.true_when, value as number | null)
  return Boolean(value)
}

export function collectPointIds(bindings: BindingMap): number[] {
  return Object.values(bindings)
    .filter((b): b is Binding => typeof b === 'object' && b !== null && 'point_id' in b)
    .map((b) => b.point_id)
}
