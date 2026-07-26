import type { ReactNode, CSSProperties } from 'react'

interface CardProps {
  title?: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
  style?: CSSProperties
  padding?: string
}

export function Card({ title, subtitle, children, actions, style, padding = '16px' }: CardProps) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      ...style,
    }}>
      {(title || actions) && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          gap: 12,
        }}>
          <div>
            {title && (
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                {title}
              </div>
            )}
            {subtitle && (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: 2 }}>
                {subtitle}
              </div>
            )}
          </div>
          {actions && <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{actions}</div>}
        </div>
      )}
      <div style={{ padding }}>{children}</div>
    </div>
  )
}
