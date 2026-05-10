import { useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { api } from '@/lib/api'
import { Clock, CheckCircle, XCircle, Edit, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { REVIEW_REVIEW_STATUS_CONFIG } from '@/lib/statusConstants'

interface HistoryItem {
  id: number
  patientId: number | null
  recommendedDrugs: string[]
  primaryDisease: string
  dpEnabled: boolean
  epsilonUsed: number | null
  reviewStatus: string | null
  createdAt: string
}

const STATUS_ICON: Record<string, JSX.Element> = {
  pending:   <Clock className="h-3.5 w-3.5" />,
  confirmed: <CheckCircle className="h-3.5 w-3.5" />,
  modified:  <Edit className="h-3.5 w-3.5" />,
  rejected:  <XCircle className="h-3.5 w-3.5" />,
}

export default function MyRecords() {
  const [records, setRecords] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    api.get<HistoryItem[]>('/api/recommendations/my-history')
      .then(setRecords)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载中...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">我的记录</h1>
            <p className="text-ia-body text-muted-foreground mt-1">查看推荐历史和医生诊疗建议</p>
          </div>
        </div>
      </section>

      {records.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground border border-dashed border-white/[0.06] rounded-lg">
          暂无推荐记录
        </div>
      ) : (
        <div className="space-y-3">
          {records.map(record => {
            const status = record.reviewStatus || 'pending'
            const cfg = REVIEW_STATUS_CONFIG[status] || REVIEW_STATUS_CONFIG.pending
            return (
              <Card key={record.id} hover="none">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-heading font-semibold">{record.primaryDisease || '未知疾病'}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {new Date(record.createdAt).toLocaleString('zh-CN')}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 600, color: cfg.color, background: cfg.bg }}>
                        {STATUS_ICON[status]} {cfg.label}
                      </span>
                      <button onClick={() => setExpandedId(expandedId === record.id ? null : record.id)} className="p-1 rounded hover:bg-surface">
                        {expandedId === record.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  {expandedId === record.id && (
                    <div className="mt-3 pt-3 border-t border-white/[0.06]">
                      <div className="text-sm text-muted-foreground mb-1">推荐药物：</div>
                      <div className="flex flex-wrap gap-1.5">
                        {record.recommendedDrugs.map((drug, i) => (
                          <span key={i} className="ia-badge ia-badge-primary">{drug}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
