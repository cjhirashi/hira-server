export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent'

interface BadgeProps {
  variant: BadgeVariant
  label: string
  dot?: boolean
}

const VARIANT_STYLES: Record<BadgeVariant, { bg: string; color: string; dot: string }> = {
  success: { bg: 'var(--success-subtle)', color: 'var(--success)',   dot: 'var(--success)' },
  warning: { bg: 'var(--warning-subtle)', color: 'var(--warning)',   dot: 'var(--warning)' },
  danger:  { bg: 'var(--danger-subtle)',  color: 'var(--danger)',    dot: 'var(--danger)' },
  info:    { bg: 'var(--info-subtle)',    color: 'var(--info)',      dot: 'var(--info)' },
  neutral: { bg: 'var(--bg-hover)',       color: 'var(--text-secondary)', dot: 'var(--text-muted)' },
  accent:  { bg: 'var(--accent-subtle)',  color: 'var(--accent)',    dot: 'var(--accent)' },
}

export function Badge({ variant, label, dot = false }: BadgeProps) {
  const s = VARIANT_STYLES[variant]
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      background: s.bg,
      color: s.color,
      borderRadius: 20,
      padding: '2px 8px',
      fontSize: 'var(--text-xs)',
      fontWeight: 600,
      whiteSpace: 'nowrap',
      lineHeight: '16px',
    }}>
      {dot && (
        <span style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: s.dot,
          flexShrink: 0,
        }} />
      )}
      {label}
    </span>
  )
}
