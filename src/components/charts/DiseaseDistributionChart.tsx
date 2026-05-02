import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const CHART_TOOLTIP_STYLE = {
  backgroundColor: '#0f2744',
  border: '1px solid rgba(14,165,233,0.20)',
  borderRadius: '8px',
  fontSize: '12px',
  color: '#f8fafc',
  boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
}

const COLORS = [
  '#0ea5e9',
  '#14b8a6',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
  '#3b82f6',
  '#8b5cf6',
  '#ec4899',
]

interface DiseaseDistributionChartProps {
  data: { name: string; count: number }[]
}

export function DiseaseDistributionChart({ data }: DiseaseDistributionChartProps) {
  return (
    <Card className="rounded-lg border border-white/[0.06] bg-surface-elevated shadow-xs">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold text-foreground">疾病分布</CardTitle>
        <CardDescription>常见慢性病统计 (Top 8)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 10, right: 10 }}>
              <defs>
                <linearGradient id="diseaseBarGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#0284c7" />
                  <stop offset="100%" stopColor="#0ea5e9" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" horizontal={false} />
              <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#94a3b8"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                width={80}
              />
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                itemStyle={{ color: '#f8fafc' }}
                formatter={(value: number) => [`${value}人`, '患者数']}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} fillOpacity={0.9} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
