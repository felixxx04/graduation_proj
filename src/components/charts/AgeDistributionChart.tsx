import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const CHART_TOOLTIP_STYLE = {
  backgroundColor: '#0f2744',
  border: '1px solid rgba(14,165,233,0.20)',
  borderRadius: '8px',
  fontSize: '12px',
  color: '#f8fafc',
  boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
}

interface AgeDistributionChartProps {
  data: { name: string; value: number; color: string }[]
}

export function AgeDistributionChart({ data }: AgeDistributionChartProps) {
  return (
    <Card className="rounded-lg border border-white/[0.06] bg-surface-elevated shadow-xs">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold text-foreground">年龄分布</CardTitle>
        <CardDescription>患者年龄段统计</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
                animationBegin={0}
                animationDuration={800}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                itemStyle={{ color: '#f8fafc' }}
                formatter={(value: number) => [`${value}人`, '数量']}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                wrapperStyle={{ color: '#cbd5e1', fontSize: '12px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
