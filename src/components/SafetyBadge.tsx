const safetyConfig: Record<string, { label: string; color: string; bg: string }> = {
  safe:                      { label: '安全',      color: '#22c55e', bg: '#052e16' },
  relative_contraindication: { label: '需谨慎',    color: '#f59e0b', bg: '#451a03' },
  off_label:                 { label: '超说明书',  color: '#f97316', bg: '#431407' },
  unverified:                { label: '待验证',    color: '#a855f7', bg: '#2e1065' },
  data_unverified:           { label: '待验证',    color: '#a855f7', bg: '#2e1065' },
}

export function SafetyBadge({ level }: { level: string }) {
  const cfg = safetyConfig[level] || { label: level || '未知', color: '#888', bg: '#111' }
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '1px 6px',
        borderRadius: '3px',
        fontSize: '11px',
        fontWeight: 600,
        color: cfg.color,
        backgroundColor: cfg.bg,
        marginLeft: '6px',
        lineHeight: '18px',
      }}
    >
      {cfg.label}
    </span>
  )
}
