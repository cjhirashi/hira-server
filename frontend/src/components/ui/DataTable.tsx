import type { ReactNode, CSSProperties } from 'react'

export interface Column<T> {
  key: string
  header: string
  render?: (row: T) => ReactNode
  style?: CSSProperties
  headerStyle?: CSSProperties
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyMessage?: string
  rowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  rowStyle?: (row: T) => CSSProperties
}

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} style={{ padding: '10px 12px' }}>
          <div style={{
            height: 14,
            borderRadius: 4,
            background: 'linear-gradient(90deg, var(--bg-elevated) 25%, var(--bg-hover) 50%, var(--bg-elevated) 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.4s infinite',
            width: `${50 + Math.random() * 40}%`,
          }} />
        </td>
      ))}
    </tr>
  )
}

export function DataTable<T>({
  columns, data, loading, emptyMessage = 'Sin datos', rowKey, onRowClick, rowStyle,
}: DataTableProps<T>) {
  return (
    <>
      <style>{`
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
      `}</style>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
          <thead>
            <tr style={{ background: 'var(--bg-elevated)' }}>
              {columns.map(col => (
                <th key={col.key} style={{
                  padding: '9px 12px',
                  textAlign: 'left',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  borderBottom: '1px solid var(--border-default)',
                  whiteSpace: 'nowrap',
                  ...col.headerStyle,
                }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} cols={columns.length} />)
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: '40px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr
                  key={rowKey(row)}
                  onClick={() => onRowClick?.(row)}
                  style={{
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                    cursor: onRowClick ? 'pointer' : 'default',
                    borderBottom: '1px solid var(--border-subtle)',
                    transition: 'background 80ms',
                    ...rowStyle?.(row),
                  }}
                  onMouseEnter={e => { if (onRowClick) (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)' }}
                  onMouseLeave={e => { if (onRowClick) (e.currentTarget as HTMLElement).style.background = '' }}
                >
                  {columns.map(col => (
                    <td key={col.key} style={{ padding: '9px 12px', color: 'var(--text-primary)', ...col.style }}>
                      {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
