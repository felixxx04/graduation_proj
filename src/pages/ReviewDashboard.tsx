import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import ReviewPanel from '../components/ReviewPanel'
import { Shield, Clock, CheckCircle, XCircle, Edit } from 'lucide-react'

interface PendingReview {
  id: number
  recommendationId: number
  patientId: number
  diseaseCn: string
  diseaseStandardized: string
  routingPath: string
  systemDrugs: string
  doctorDecision: string | null
  createdAt: string
}

interface DrugOption {
  drugName: string
  englishName: string
  category: string
  safetyType: string
  score: number
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: JSX.Element }> = {
  confirm: { label: '已确认', color: '#22c55e', icon: <CheckCircle className="h-4 w-4" /> },
  modify:  { label: '已修改', color: '#60a5fa', icon: <Edit className="h-4 w-4" /> },
  reject:  { label: '已拒绝', color: '#f87171', icon: <XCircle className="h-4 w-4" /> },
}

function parseDrugs(systemDrugs: string): DrugOption[] {
  try { return JSON.parse(systemDrugs) } catch { return [] }
}

export default function ReviewDashboard() {
  const [pendingReviews, setPendingReviews] = useState<PendingReview[]>([])
  const [selectedReview, setSelectedReview] = useState<PendingReview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPending = async () => {
    setLoading(true)
    try {
      const data = await api.get<PendingReview[]>('/api/review/pending')
      setPendingReviews(data)
    } catch { setError('获取待审核列表失败') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchPending() }, [])

  const handleSubmitReview = async (
    decision: 'confirm' | 'modify' | 'reject',
    selectedDrug?: string,
    reason?: string,
    template?: string,
    advice?: string,
  ) => {
    if (!selectedReview) return
    try {
      await api.post('/api/review/log', {
        recommendationId: selectedReview.recommendationId,
        patientId: selectedReview.patientId,
        diseaseCn: selectedReview.diseaseCn,
        diseaseStandardized: selectedReview.diseaseStandardized,
        routingPath: selectedReview.routingPath,
        systemDrugs: selectedReview.systemDrugs,
        doctorDecision: decision,
        doctorSelectedDrug: selectedDrug || null,
        doctorReason: reason || null,
        treatmentTemplate: template || null,
        treatmentAdvice: advice || null,
      })
      setSelectedReview(null)
      fetchPending()
    } catch { setError('提交审核失败') }
  }

  const statusBadge = (decision: string | null) => {
    if (!decision) return <Clock className="h-4 w-4 text-muted-foreground" />
    const cfg = STATUS_CONFIG[decision]
    if (!cfg) return <Clock className="h-4 w-4 text-muted-foreground" />
    return <span style={{ color: cfg.color }}>{cfg.icon}</span>
  }

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载中...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <Shield className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">推荐审核</h1>
            <p className="text-ia-body text-muted-foreground mt-1">审核患者的用药推荐，出具诊疗建议</p>
          </div>
        </div>
      </section>

      {error && <div className="p-3 rounded-sm bg-destructive/6 border border-destructive/30 text-destructive text-sm">{error}</div>}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          <h3 className="font-heading font-semibold text-sm text-muted-foreground mb-2">待审核 ({pendingReviews.length})</h3>
          {pendingReviews.length === 0 && <p className="text-sm text-muted-foreground">暂无待审核推荐</p>}
          {pendingReviews.map(review => (
            <div key={review.id} onClick={() => setSelectedReview(review)}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                selectedReview?.id === review.id ? 'border-brand-sky bg-brand-sky/5' : 'border-white/[0.06] bg-surface hover:bg-surface-elevated'
              }`}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-heading font-semibold text-sm">{review.diseaseCn}</span>
                  {review.diseaseStandardized && <span className="text-xs text-muted-foreground ml-2">→ {review.diseaseStandardized}</span>}
                </div>
                {statusBadge(review.doctorDecision)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">{new Date(review.createdAt).toLocaleDateString('zh-CN')}</div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2">
          {selectedReview ? (
            <Card hover="none">
              <CardHeader><CardTitle className="text-base">审核详情</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                  <div className="text-sm text-muted-foreground">患者症状</div>
                  <div className="font-heading font-semibold mt-1">{selectedReview.diseaseCn}</div>
                  {selectedReview.routingPath && (
                    <>
                      <div className="text-sm text-muted-foreground mt-3">路由路径</div>
                      <div className="text-xs mt-1" style={{ color: '#00d4aa' }}>{selectedReview.routingPath}</div>
                    </>
                  )}
                </div>
                <ReviewPanel
                  recommendationId={selectedReview.recommendationId}
                  diseaseCn={selectedReview.diseaseCn}
                  drugs={parseDrugs(selectedReview.systemDrugs)}
                  onSubmitReview={handleSubmitReview}
                />
              </CardContent>
            </Card>
          ) : (
            <div className="p-8 text-center text-muted-foreground border border-dashed border-white/[0.06] rounded-lg">
              选择左侧待审核记录查看详情
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
