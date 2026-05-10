export const REVIEW_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: '待审核', color: '#888', bg: '#1a1a2e' },
  confirmed: { label: '已确认', color: '#22c55e', bg: '#052e16' },
  modified:  { label: '已修改', color: '#60a5fa', bg: '#1e3a5f' },
  rejected:  { label: '已拒绝', color: '#f87171', bg: '#450a0a' },
}
