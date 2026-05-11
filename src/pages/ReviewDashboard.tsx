import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import ReviewPanel from '../components/ReviewPanel'
import { Shield, Clock } from 'lucide-react'

interface PendingReview {
  recommendationId: number
  patientId: number | null
  inputData: string
  resultData: string
  reviewStatus: string
  createdAt: string
}

interface DrugOption {
  drugName: string
  englishName: string
  category: string
  safetyType: string
  score: number
}

function parseInputDisease(inputData: string): string {
  try {
    const parsed = JSON.parse(inputData)
    return parsed.diseases || parsed.disease || ''
  } catch { return '' }
}

function parseResultDrugs(resultData: string): DrugOption[] {
  try {
    const parsed = JSON.parse(resultData)
    const selected = parsed.selected || []
    return selected.map((item: any) => ({
      drugName: item.drugName || '',
      englishName: item.englishName || '',
      category: item.category || '',
      safetyType: item.safetyType || 'safe',
      score: item.score || 0,
    }))
  } catch { return [] }
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

  const diseaseCn = selectedReview ? parseInputDisease(selectedReview.inputData) : ''
  const drugs = selectedReview ? parseResultDrugs(selectedReview.resultData) : []

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
        diseaseCn,
        diseaseStandardized: '',
        routingPath: '',
        systemDrugs: selectedReview.resultData,
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
          {pendingReviews.map(review => {
            const disease = parseInputDisease(review.inputData)
            return (
              <div key={review.recommendationId} onClick={() => setSelectedReview(review)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedReview?.recommendationId === review.recommendationId ? 'border-brand-sky bg-brand-sky/5' : 'border-white/[0.06] bg-surface hover:bg-surface-elevated'
                }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-heading font-semibold text-sm">{disease || '未知疾病'}</span>
                  </div>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-xs text-muted-foreground mt-1">{new Date(review.createdAt).toLocaleDateString('zh-CN')}</div>
              </div>
            )
          })}
        </div>

        <div className="lg:col-span-2">
          {selectedReview ? (
            <Card hover="none">
              <CardHeader><CardTitle className="text-base">审核详情</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                  <div className="text-sm text-muted-foreground">患者症状</div>
                  <div className="font-heading font-semibold mt-1">{diseaseCn || '未提供'}</div>
                </div>
                <ReviewPanel
                  recommendationId={selectedReview.recommendationId}
                  diseaseCn={diseaseCn}
                  drugs={drugs}
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
