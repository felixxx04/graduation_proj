import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { usePrivacyStore } from '@/lib/privacyStore'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { BarChart3, TrendingUp, Activity, Shield, Sparkles } from 'lucide-react'

export default function RecommendationStats() {
  const { config, budget } = usePrivacyStore()
  const [stats, setStats] = useState<{ totalRecommendations: number; statusDistribution: Record<string, number> } | null>(null)
  const [demoDisease, setDemoDisease] = useState('')
  const [demoResult, setDemoResult] = useState<any>(null)
  const [demoLoading, setDemoLoading] = useState(false)

  useEffect(() => {
    api.get<{ totalRecommendations: number; statusDistribution: Record<string, number> }>('/api/stats/recommendations')
      .then(setStats).catch(() => {})
  }, [])

  const handleDemo = async () => {
    if (!demoDisease.trim()) return
    setDemoLoading(true)
    try {
      const result = await api.post('/api/recommendations/generate', { diseases: demoDisease, dpEnabled: false, topK: 4 })
      setDemoResult(result)
    } catch {}
    finally { setDemoLoading(false) }
  }

  const statusLabels: Record<string, string> = { pending: '待审核', confirmed: '已确认', modified: '已修改', rejected: '已拒绝' }
  const statusColors: Record<string, string> = { pending: '#888', confirmed: '#22c55e', modified: '#60a5fa', rejected: '#f87171' }
  const statusData = stats ? Object.entries(stats.statusDistribution).map(([k, v]) => ({
    name: statusLabels[k] || k, value: v, color: statusColors[k] || '#888',
  })) : []

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">推荐统计</h1>
            <p className="text-ia-body text-muted-foreground mt-1">推荐分布统计与实时路由演示</p>
          </div>
        </div>
      </section>

      <div className="grid md:grid-cols-3 gap-4">
        <Card hover="none"><CardContent className="p-4 text-center">
          <TrendingUp className="h-5 w-5 text-brand-sky mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold">{stats?.totalRecommendations || 0}</div>
          <div className="text-sm text-muted-foreground">总推荐次数</div>
        </CardContent></Card>
        <Card hover="none"><CardContent className="p-4 text-center">
          <Activity className="h-5 w-5 text-secondary mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold">{stats?.statusDistribution?.pending || 0}</div>
          <div className="text-sm text-muted-foreground">待审核</div>
        </CardContent></Card>
        <Card hover="none"><CardContent className="p-4 text-center">
          <Shield className="h-5 w-5 text-green-500 mx-auto mb-2" />
          <div className="text-2xl font-heading font-bold">{budget.remaining.toFixed(1)} / {config.privacyBudget.toFixed(1)}</div>
          <div className="text-sm text-muted-foreground">隐私预算剩余</div>
        </CardContent></Card>
      </div>

      {statusData.length > 0 && (
        <Card hover="none">
          <CardHeader><CardTitle className="text-base">审核状态分布</CardTitle></CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="name" stroke="#888" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#888" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '4px', fontSize: '12px' }} />
                  <Bar dataKey="value" name="数量">{statusData.map((entry, i) => <Cell key={i} fill={entry.color} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      <Card hover="none">
        <CardHeader><CardTitle className="text-base">实时路由演示</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Input value={demoDisease} onChange={e => setDemoDisease(e.target.value)} placeholder="输入疾病名，如：高血压、感冒、腹泻..." className="flex-1" />
            <Button onClick={handleDemo} loading={demoLoading} className="gap-2"><Sparkles className="h-4 w-4" /> 演示</Button>
          </div>
          {demoResult?.selected && (
            <div className="space-y-2 mt-4">
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
