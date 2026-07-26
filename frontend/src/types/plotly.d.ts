// Minimal type declaration for react-plotly.js to avoid TypeScript module-not-found error.
// Full types come from @types/react-plotly.js when available.
declare module 'react-plotly.js' {
  import { Component, CSSProperties } from 'react'

  interface PlotParams {
    data: Record<string, unknown>[]
    layout?: Record<string, unknown>
    config?: Record<string, unknown>
    style?: CSSProperties
    className?: string
    useResizeHandler?: boolean
    [key: string]: unknown
  }

  export default class Plot extends Component<PlotParams> {}
}
