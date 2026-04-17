import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const CHART_TOOLTIP_STYLE = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '3px',
  fontSize: '11px',
}

const COLORS = [
  'hsl(var(--ia-data-1))',
  'hsl(var(--ia-data-2))',
  'hsl(var(--ia-data-3))',
  'hsl(var(--ia-data-4))',
  'hsl(var(--ia-data-5))',
  'hsl(var(--primary))',
  'hsl(var(--secondary))',
  'hsl(var(--muted-foreground))',
]

interface DiseaseDistributionChartProps {
  data: { name: string; count: number }[]
}

export function DiseaseDistributionChart({ data }: DiseaseDistributionChartProps) {
  return (
    <Card className="border border-ia-border bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-ia-card-title font-heading">疾病分布</CardTitle>
        <CardDescription>常见慢性病统计 (Top 8)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="hsl(var(--muted-foreground))"
                tick={{ fontSize: 11 }}
                width={80}
              />
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                formatter={(value: number) => [`${value}人`, '患者数']}
              />
              <Bar dataKey="count" radius={[0, 2, 2, 0]} barSize={16}>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
