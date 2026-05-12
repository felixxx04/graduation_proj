import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { usePrivacyStore } from '@/lib/privacyStore'
import { REVIEW_STATUS_CONFIG } from '@/lib/statusConstants'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from 'recharts'
import TreemapChart from '../components/TreemapChart'
import { BarChart3, TrendingUp, Activity, Shield, Sparkles, Pill } from 'lucide-react'

interface StatsData {
  totalRecommendations: number
  statusDistribution: Record<string, number>
  approvalRate: number
  approvalTotal: number
  approvalConfirmed: number
  uniqueDrugCount: number
  trend: { day: string; count: number }[]
  topDrugs: { name: string; count: number }[]
  categoryDistribution: { name: string; value: number }[]
}
export default function RecommendationStats() {
  const { config, budget } = usePrivacyStore()
  const [stats, setStats] = useState<StatsData | null>(null)
  const [demoDisease, setDemoDisease] = useState('')
  const [demoResult, setDemoResult] = useState<any>(null)
  const [demoLoading, setDemoLoading] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.get<StatsData>('/api/stats/recommendations')
        setStats(data)
      } catch { /* silent */ }
      finally { setLoading(false) }
    }
    fetchStats()
  }, [])

  const handleDemo = async () => {
    if (!demoDisease.trim()) return
    setDemoLoading(true)
    try {
      const result = await api.post('/api/recommendations/generate', { diseases: demoDisease, dpEnabled: false, topK: 4 })
      setDemoResult(result)
    } catch { /* silent */ }
    finally { setDemoLoading(false) }
  }

  const statusData = stats ? Object.entries(stats.statusDistribution).map(([k, v]) => ({
    name: REVIEW_STATUS_CONFIG[k]?.label || k,
    value: v,
    color: REVIEW_STATUS_CONFIG[k]?.color || '#888',
  })) : []

  // Merge small categories into "其他" for treemap readability
  const mergedCategories = (stats?.categoryDistribution || []).length > 8
    ? [
        ...(stats?.categoryDistribution || []).slice(0, 6),
        {
          name: '其他',
          value: (stats?.categoryDistribution || []).slice(6).reduce((s: number, c: {value: number}) => s + c.value, 0),
        },
      ]
    : (stats?.categoryDistribution || [])

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载统计数据...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">推荐统计</h1>
            <p className="text-ia-body text-muted-foreground mt-1">推荐分布统计 · 药物分析 · 审核概览</p>
          </div>
        </div>
      </section>

      {/* 指标卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <Card hover="none"><CardContent className="p-5 text-center">
          <TrendingUp className="h-5 w-5 text-brand-sky mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold text-brand-sky">{stats?.totalRecommendations || 0}</div>
          <div className="text-sm text-muted-foreground">总推荐次数</div>
        </CardContent></Card>
        <Card hover="none"><CardContent className="p-5 text-center">
          <Activity className="h-5 w-5 text-amber-400 mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold text-amber-400">{stats?.statusDistribution?.pending || 0}</div>
          <div className="text-sm text-muted-foreground">待审核</div>
        </CardContent></Card>
        <Card hover="none"><CardContent className="p-5 text-center">
          <Shield className="h-5 w-5 text-green-500 mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold text-green-500">{stats?.approvalRate || 0}%</div>
          <div className="text-sm text-muted-foreground">审核通过率</div>
        </CardContent></Card>
        <Card hover="none"><CardContent className="p-5 text-center">
          <Pill className="h-5 w-5 text-purple-400 mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold text-purple-400">{stats?.uniqueDrugCount || 0}</div>
          <div className="text-sm text-muted-foreground">涉及药物数</div>
        </CardContent></Card>
      </div>

      {/* 2x2 图表 */}
      <div className="grid grid-cols-2 gap-5">
        {/* 推荐趋势 */}
        <Card hover="none">
          <CardHeader><CardTitle className="text-base">推荐趋势</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={stats?.trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="day" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#0f1d32', border: '1px solid #334155', borderRadius: 4, fontSize: 12, color: '#e2e8f0' }} />
                <Line type="monotone" dataKey="count" stroke="#38bdf8" strokeWidth={2} dot={{ fill: '#38bdf8', r: 3 }} name="推荐数" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 药物频次 Top 10 */}
        <Card hover="none">
          <CardHeader><CardTitle className="text-base">药物推荐频次 Top 10</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stats?.topDrugs || []} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis dataKey="name" type="category" stroke="#64748b" tick={{ fontSize: 11, fill: '#cbd5e1' }} width={90} />
                <Tooltip contentStyle={{ background: '#0f1d32', border: '1px solid #334155', borderRadius: 4, fontSize: 12, color: '#e2e8f0' }} />
                <Bar dataKey="count" fill="#38bdf8" radius={[0, 3, 3, 0]} name="次数" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 药物分类占比 — Treemap */}
        <Card hover="none">
          <CardHeader><CardTitle className="text-base">药物分类分布</CardTitle></CardHeader>
          <CardContent>
            <TreemapChart data={mergedCategories} />
          </CardContent>
        </Card>

        {/* 审核状态分布 — 进度条 */}
        <Card hover="none">
          <CardHeader><CardTitle className="text-base">审核状态分布</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3 pt-1">
              {statusData.map((item) => {
                const maxVal = Math.max(...statusData.map(d => d.value), 1)
                return (
                  <div key={item.name}>
                    <div className="flex justify-between text-xs mb-1">
                      <span style={{ color: item.color }}>{item.name}</span>
                      <span className="text-muted-foreground">{item.value}</span>
                    </div>
                    <div className="h-5 rounded-sm overflow-hidden" style={{ background: '#1e293b' }}>
                      <div
                        className="h-full rounded-sm transition-all duration-500"
                        style={{ width: `${(item.value / maxVal) * 100}%`, background: item.color }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 隐私预算 + 实时路由演示 */}
      <Card hover="none">
        <CardHeader><CardTitle className="text-base">隐私预算 · 实时演示</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="p-3 rounded-sm bg-surface border border-white/[0.06] text-center">
              <div className="text-xs text-muted-foreground mb-1">当前 ε</div>
              <div className="font-heading font-bold text-brand-sky">{config.epsilon.toFixed(3)}</div>
            </div>
            <div className="p-3 rounded-sm bg-surface border border-white/[0.06] text-center">
              <div className="text-xs text-muted-foreground mb-1">预算剩余</div>
              <div className="font-heading font-bold text-secondary">{budget.remaining.toFixed(2)} / {config.privacyBudget.toFixed(1)}</div>
            </div>
            <div className="p-3 rounded-sm bg-surface border border-white/[0.06] text-center">
              <div className="text-xs text-muted-foreground mb-1">确认 / 总计</div>
              <div className="font-heading font-bold text-green-400">{stats?.approvalConfirmed || 0} / {stats?.approvalTotal || 0}</div>
            </div>
          </div>

          <div className="flex gap-3">
            <Input value={demoDisease} onChange={e => setDemoDisease(e.target.value)} placeholder="输入疾病名查看路由过程，如：高血压" className="flex-1" />
            <Button onClick={handleDemo} loading={demoLoading} className="gap-2"><Sparkles className="h-4 w-4" /> 演示</Button>
          </div>
          {demoResult?.selected && (
            <div className="space-y-2">
              {demoResult.selected.map((item: any, i: number) => (
                <div key={i} className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    <span className="font-heading font-semibold">{item.drugName}</span>
                    <span className="ia-badge ia-badge-primary text-[10px]">{item.category}</span>
                    <span className="text-xs text-muted-foreground">score: {item.score?.toFixed(3)}</span>
                  </div>
                  {item.routingPath && <div className="text-xs mt-1" style={{ color: '#00d4aa' }}>{item.routingPath}</div>}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
