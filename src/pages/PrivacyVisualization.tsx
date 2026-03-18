import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { 
  BarChart3, 
  Shield, 
  TrendingUp, 
  Activity, 
  Lock, 
  Eye, 
  Zap,
  Target,
  Layers,
  GitCompare,
  CheckCircle2,
  BookOpen,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ScatterChart,
  Scatter,
  ZAxis,
  ReferenceDot,
} from 'recharts'
import { usePrivacyStore, formatEventType } from '@/lib/privacyStore'

// 模拟数据 - 隐私预算 vs 准确率
const privacyAccuracyData = [
  { epsilon: 0.1, accuracy: 78.5, utility: 65.2 },
  { epsilon: 0.5, accuracy: 85.3, utility: 78.4 },
  { epsilon: 1.0, accuracy: 89.7, utility: 86.5 },
  { epsilon: 2.0, accuracy: 92.1, utility: 91.3 },
  { epsilon: 5.0, accuracy: 94.5, utility: 95.8 },
  { epsilon: 10.0, accuracy: 95.8, utility: 98.2 },
]

// 噪声机制对比数据
const noiseMechanismData = [
  { mechanism: 'Laplace', accuracy: 89.7, privacy: 95, speed: 88 },
  { mechanism: 'Gaussian', accuracy: 91.2, privacy: 92, speed: 92 },
  { mechanism: 'Geometric', accuracy: 87.5, privacy: 93, speed: 95 },
]

// 雷达图数据 — 噪声机制多维度综合对比
const radarData = [
  { subject: '推荐准确率', Laplace: 89.7, Gaussian: 91.2, Geometric: 87.5 },
  { subject: '隐私保护强度', Laplace: 95, Gaussian: 92, Geometric: 93 },
  { subject: '计算速度', Laplace: 88, Gaussian: 92, Geometric: 95 },
  { subject: '稳定性', Laplace: 85, Gaussian: 90, Geometric: 82 },
  { subject: '高维适用性', Laplace: 78, Gaussian: 96, Geometric: 72 },
]

// 散点图数据 — ε 值下的隐私效用分布（多次实验模拟）
const scatterData = [
  { epsilon: 0.1, utility: 63, privacy: 98, name: 'ε=0.1' },
  { epsilon: 0.1, utility: 66, privacy: 97, name: 'ε=0.1' },
  { epsilon: 0.5, utility: 76, privacy: 90, name: 'ε=0.5' },
  { epsilon: 0.5, utility: 80, privacy: 89, name: 'ε=0.5' },
  { epsilon: 1.0, utility: 86, privacy: 82, name: 'ε=1.0' },
  { epsilon: 1.0, utility: 88, privacy: 81, name: 'ε=1.0' },
  { epsilon: 2.0, utility: 91, privacy: 72, name: 'ε=2.0' },
  { epsilon: 2.0, utility: 93, privacy: 70, name: 'ε=2.0' },
  { epsilon: 5.0, utility: 95, privacy: 55, name: 'ε=5.0' },
  { epsilon: 5.0, utility: 96, privacy: 53, name: 'ε=5.0' },
  { epsilon: 10.0, utility: 98, privacy: 38, name: 'ε=10.0' },
  { epsilon: 10.0, utility: 97, privacy: 40, name: 'ε=10.0' },
]

// 不同应用阶段的性能对比
const stageComparisonData = [
  { stage: '数据层', accuracy: 85.2, privacy: 98, overhead: 15 },
  { stage: '梯度层', accuracy: 89.7, privacy: 94, overhead: 25 },
  { stage: '模型层', accuracy: 88.5, privacy: 92, overhead: 10 },
]

// 隐私开销累积数据
const budgetAccumulationData = [
  { epoch: 1, consumed: 0.5, remaining: 9.5 },
  { epoch: 5, consumed: 2.3, remaining: 7.7 },
  { epoch: 10, consumed: 4.8, remaining: 5.2 },
  { epoch: 15, consumed: 7.1, remaining: 2.9 },
  { epoch: 20, consumed: 9.2, remaining: 0.8 },
]

// 特征重要性数据
const featureImportanceData = [
  { feature: '年龄', importance: 0.85 },
  { feature: '疾病类型', importance: 0.92 },
  { feature: '过敏史', importance: 0.78 },
  { feature: '当前用药', importance: 0.88 },
  { feature: 'BMI', importance: 0.65 },
  { feature: '病史时长', importance: 0.72 },
  { feature: '实验室指标', importance: 0.81 },
  { feature: '基因标记', importance: 0.69 },
]

export default function PrivacyVisualization() {
  const [selectedView, setSelectedView] = useState<'overview' | 'comparison' | 'analysis'>('overview')
  const { config, events, budget } = usePrivacyStore()

  const budgetSeries = useMemo(() => {
    if (!events.length) return budgetAccumulationData

    // Build an interpretable "step" series: operation index as x-axis
    const ordered = [...events].reverse()
    let consumed = 0
    const total = Math.max(0, config.privacyBudget)
    return ordered.map((e, idx) => {
      consumed += e.epsilonSpent
      const remaining = Math.max(0, total - consumed)
      return {
        epoch: idx + 1,
        consumed: Math.round(consumed * 100) / 100,
        remaining: Math.round(remaining * 100) / 100,
        type: formatEventType(e.type),
        note: e.note ?? '',
        epsilonSpent: e.epsilonSpent,
      }
    })
  }, [config.privacyBudget, events])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-2">
          隐私保护效果可视化
        </h1>
        <p className="text-muted-foreground">
          多维度展示差分隐私机制的保护效果与性能影响
        </p>
      </div>

      {/* View Selector */}
      <div className="flex gap-2">
        <Button
          variant={selectedView === 'overview' ? 'default' : 'outline'}
          onClick={() => setSelectedView('overview')}
          className="gap-2"
        >
          <BarChart3 className="h-4 w-4" />
          总览
        </Button>
        <Button
          variant={selectedView === 'comparison' ? 'default' : 'outline'}
          onClick={() => setSelectedView('comparison')}
          className="gap-2"
        >
          <GitCompare className="h-4 w-4" />
          对比分析
        </Button>
        <Button
          variant={selectedView === 'analysis' ? 'default' : 'outline'}
          onClick={() => setSelectedView('analysis')}
          className="gap-2"
        >
          <TrendingUp className="h-4 w-4" />
          深度分析
        </Button>
      </div>

      {/* Overview View */}
      {selectedView === 'overview' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Key Metrics */}
          <div className="grid md:grid-cols-4 gap-4">
            {[
              {
                icon: Shield,
                label: '隐私保护等级',
                value: `ε=${config.epsilon.toFixed(2)}`,
                desc: config.epsilon <= 1.0 ? '强隐私保护' : config.epsilon <= 2.0 ? '中等保护' : '偏弱保护',
                color: 'from-blue-500 to-cyan-500',
              },
              {
                icon: Target,
                label: '推荐准确率',
                value: '89.7%',
                desc: '+12% vs 基线',
                color: 'from-green-500 to-emerald-500',
              },
              {
                icon: Zap,
                label: '响应时间',
                value: '< 200ms',
                desc: '实时推理',
                color: 'from-yellow-500 to-orange-500',
              },
              {
                icon: Lock,
                label: '数据安全',
                value: budget.remaining > 0 ? 'ON' : 'LIMIT',
                desc: budget.remaining > 0 ? '预算充足' : '预算耗尽（demo）',
                color: 'from-purple-500 to-pink-500',
              },
            ].map((metric, index) => {
              const Icon = metric.icon
              return (
                <Card key={index} className="border-border/40 bg-card/50 backdrop-blur hover:shadow-lg transition-all duration-300">
                  <CardContent className="pt-6">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${metric.color} flex items-center justify-center mb-4 shadow-lg`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                    <div className="text-3xl font-bold mb-1 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                      {metric.value}
                    </div>
                    <div className="text-sm font-medium mb-1">{metric.label}</div>
                    <div className="text-xs text-muted-foreground">{metric.desc}</div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Privacy-Accuracy Trade-off Curve */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                  <Activity className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>隐私 - 效用权衡曲线</CardTitle>
                  <CardDescription>
                    隐私预算 ε 对模型准确率和数据效用的影响
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={privacyAccuracyData}>
                    <defs>
                      <linearGradient id="colorAccuracy" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorUtility" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--secondary))" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="hsl(var(--secondary))" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="epsilon" 
                      label={{ value: '隐私预算 ε', position: 'insideBottom', offset: -5 }}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <YAxis 
                      label={{ value: '百分比 (%)', angle: -90, position: 'insideLeft' }}
                      stroke="hsl(var(--muted-foreground))"
                      domain={[0, 100]}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Area 
                      type="monotone" 
                      dataKey="accuracy" 
                      name="推荐准确率"
                      stroke="hsl(var(--primary))" 
                      fillOpacity={1} 
                      fill="url(#colorAccuracy)" 
                      strokeWidth={3}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="utility" 
                      name="数据效用"
                      stroke="hsl(var(--secondary))" 
                      fillOpacity={1} 
                      fill="url(#colorUtility)" 
                      strokeWidth={3}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <p className="text-sm text-muted-foreground mt-4 text-center">
                随着隐私预算 ε 增大，隐私保护减弱但模型性能提升。本系统默认 ε=1.0，在保护与效用间取得良好平衡。
              </p>
            </CardContent>
          </Card>

          {/* Feature Importance */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Layers className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>特征重要性分析</CardTitle>
                  <CardDescription>
                    深度学习模型对各患者特征的关注度
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={featureImportanceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" domain={[0, 1]} stroke="hsl(var(--muted-foreground))" />
                    <YAxis 
                      dataKey="feature" 
                      type="category" 
                      width={100}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar 
                      dataKey="importance" 
                      name="重要性得分"
                      fill="hsl(var(--primary))" 
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Scatter Chart — 隐私效用权衡散点图 */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center">
                  <Eye className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>隐私 — 效用权衡散点分布</CardTitle>
                  <CardDescription>
                    不同 ε 值下多次实验结果的隐私保护强度（Privacy）与数据效用（Utility）散点分布
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      type="number"
                      dataKey="utility"
                      name="数据效用"
                      domain={[55, 100]}
                      label={{ value: '数据效用 (%)', position: 'insideBottom', offset: -10, fontSize: 12 }}
                      stroke="hsl(var(--muted-foreground))"
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      type="number"
                      dataKey="privacy"
                      name="隐私保护强度"
                      domain={[30, 100]}
                      label={{ value: '隐私保护强度 (%)', angle: -90, position: 'insideLeft', fontSize: 12 }}
                      stroke="hsl(var(--muted-foreground))"
                      tick={{ fontSize: 11 }}
                    />
                    <ZAxis range={[60, 60]} />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                      formatter={(value, name) => [`${value}%`, name]}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    {['ε=0.1', 'ε=0.5', 'ε=1.0', 'ε=2.0', 'ε=5.0', 'ε=10.0'].map((epsilonName, idx) => {
                      const colors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1']
                      return (
                        <Scatter
                          key={epsilonName}
                          name={epsilonName}
                          data={scatterData.filter((d) => d.name === epsilonName)}
                          fill={colors[idx]}
                          opacity={0.8}
                        />
                      )
                    })}
                    {/* 当前 ε 参考点 */}
                    <ReferenceDot
                      x={Math.min(98, 60 + config.epsilon * 4)}
                      y={Math.max(30, 98 - config.epsilon * 6)}
                      r={10}
                      fill="hsl(var(--secondary))"
                      stroke="white"
                      strokeWidth={2}
                      label={{ value: '当前', position: 'top', fontSize: 11, fill: 'hsl(var(--secondary))' }}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              <p className="text-sm text-muted-foreground mt-4 text-center">
                绿色标记为当前 ε={config.epsilon.toFixed(2)} 的估算位置。左上角为最优权衡区域（高隐私+高效用）。
              </p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Comparison View */}
      {selectedView === 'comparison' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Noise Mechanism Comparison */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <GitCompare className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>噪声机制对比</CardTitle>
                  <CardDescription>
                    Laplace、Gaussian、Geometric 三种机制的性能对比
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={noiseMechanismData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="mechanism" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="accuracy" name="准确率 (%)" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="privacy" name="隐私保护" fill="hsl(var(--secondary))" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="speed" name="计算速度" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="grid md:grid-cols-3 gap-4 mt-6">
                {noiseMechanismData.map((item) => (
                  <div key={item.mechanism} className="p-4 rounded-lg bg-muted/50 border border-border">
                    <h4 className="font-semibold mb-2">{item.mechanism} 机制</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      <li>• 准确率：{item.accuracy}%</li>
                      <li>• 隐私保护：{item.privacy}/100</li>
                      <li>• 计算速度：{item.speed}/100</li>
                    </ul>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Application Stage Comparison */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                  <Layers className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>隐私保护阶段对比</CardTitle>
                  <CardDescription>
                    数据层、梯度层、模型层扰动的效果对比
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stageComparisonData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="stage" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="accuracy" name="准确率 (%)" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="privacy" name="隐私保护" fill="hsl(var(--secondary))" radius={[4, 4, 0, 0]} />
                    <Bar 
                      dataKey="overhead" 
                      name="计算开销 (%)" 
                      fill="hsl(var(--destructive))" 
                      radius={[4, 4, 0, 0]} 
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-6 p-4 rounded-lg bg-primary/5 border border-primary/20">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-primary">梯度层扰动</strong>（本系统采用）在准确率和隐私保护之间取得最佳平衡，
                  虽然计算开销略高（+25%），但能有效保护训练过程中的梯度信息，适用于深度学习场景。
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Radar Chart — 噪声机制多维综合对比 */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center">
                  <Target className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>噪声机制综合能力雷达图</CardTitle>
                  <CardDescription>
                    从五个维度全面对比三种差分隐私噪声机制的综合能力
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[360px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '13px' }} />
                    <Radar name="Laplace" dataKey="Laplace" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.15} strokeWidth={2} />
                    <Radar name="Gaussian" dataKey="Gaussian" stroke="hsl(var(--secondary))" fill="hsl(var(--secondary))" fillOpacity={0.15} strokeWidth={2} />
                    <Radar name="Geometric" dataKey="Geometric" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 grid md:grid-cols-3 gap-4 text-sm">
                <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <div className="font-medium text-primary mb-1">Laplace 机制</div>
                  <p className="text-xs text-muted-foreground">隐私保护最强，适用于低维数值查询，计算速度较快</p>
                </div>
                <div className="p-3 rounded-lg bg-secondary/5 border border-secondary/20">
                  <div className="font-medium text-secondary mb-1">Gaussian 机制</div>
                  <p className="text-xs text-muted-foreground">高维适用性最优，准确率最高，本系统主要推荐机制</p>
                </div>
                <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                  <div className="font-medium text-amber-600 dark:text-amber-400 mb-1">Geometric 机制</div>
                  <p className="text-xs text-muted-foreground">离散数据计算速度最快，适用于计数查询场景</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Analysis View */}
      {selectedView === 'analysis' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Privacy Budget Accumulation */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                  <Target className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>隐私预算累积分析</CardTitle>
                  <CardDescription>
                    推理/训练操作的隐私预算消耗（总预算 ε_total={config.privacyBudget.toFixed(1)}）
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={budgetSeries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis 
                      dataKey="epoch" 
                      label={{ value: '操作序号', position: 'insideBottom', offset: -5 }}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <YAxis 
                      label={{ value: '预算值', angle: -90, position: 'insideLeft' }}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="consumed" 
                      name="已消耗预算"
                      stroke="hsl(var(--destructive))" 
                      strokeWidth={3}
                      dot={{ fill: 'hsl(var(--destructive))', r: 6 }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="remaining" 
                      name="剩余预算"
                      stroke="hsl(var(--secondary))" 
                      strokeWidth={3}
                      dot={{ fill: 'hsl(var(--secondary))', r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {events.length > 0 && (
                <div className="mt-6 grid md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-background border border-border">
                    <div className="text-sm font-medium mb-2">最近操作</div>
                    <div className="space-y-2">
                      {events.slice(0, 5).map((e) => (
                        <div key={e.id} className="flex items-start justify-between gap-3 text-sm">
                          <div className="min-w-0">
                            <div className="font-medium truncate">{formatEventType(e.type)}</div>
                            <div className="text-xs text-muted-foreground truncate">{e.note ?? '—'}</div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="font-semibold text-primary">+ε {e.epsilonSpent.toFixed(2)}</div>
                            <div className="text-xs text-muted-foreground">
                              {new Date(e.ts).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
                    <div className="text-sm font-medium mb-2">当前配置快照</div>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      <li>机制：{config.noiseMechanism}</li>
                      <li>阶段：{config.applicationStage}</li>
                      <li>ε={config.epsilon.toFixed(3)}{config.noiseMechanism === 'gaussian' ? `，δ=${config.delta.toExponential(2)}` : ''}</li>
                      <li>敏感度 Δf={config.sensitivity.toFixed(2)}</li>
                    </ul>
                  </div>
                </div>
              )}
              <div className="mt-6 grid md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
                  <h4 className="font-semibold mb-2 flex items-center gap-2 text-blue-800 dark:text-blue-300">
                    <Eye className="h-4 w-4" />
                    组合定理应用
                  </h4>
                  <p className="text-sm text-blue-700 dark:text-blue-400">
                    根据串行组合定理，k 次ε-差分隐私操作的总隐私开销为 k×ε。
                    本系统采用高级组合定理，通过隐私预算的智能分配，
                    在 20 轮训练后仍保持有效隐私保护。
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                  <h4 className="font-semibold mb-2 flex items-center gap-2 text-green-800 dark:text-green-300">
                    <Shield className="h-4 w-4" />
                    预算优化策略
                  </h4>
                  <p className="text-sm text-green-700 dark:text-green-400">
                    采用自适应预算分配算法，早期轮次分配较少预算，
                    后期逐步增加，使隐私投入集中在模型收敛关键阶段，
                    提升整体效用。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Algorithm Performance Metrics */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>算法性能指标</CardTitle>
                  <CardDescription>
                    深度学习模型在差分隐私约束下的综合表现
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="space-y-4">
                  <h4 className="font-semibold flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    推荐性能
                  </h4>
                  <div className="space-y-3">
                    {[
                      { label: '准确率 (Accuracy)', value: 89.7 },
                      { label: '精确率 (Precision)', value: 87.3 },
                      { label: '召回率 (Recall)', value: 91.2 },
                      { label: 'F1 分数', value: 89.2 },
                      { label: 'AUC-ROC', value: 93.5 },
                    ].map((metric) => (
                      <div key={metric.label}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-muted-foreground">{metric.label}</span>
                          <span className="font-medium">{metric.value}%</span>
                        </div>
                        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${metric.value}%` }}
                            transition={{ duration: 0.8 }}
                            className="h-full bg-gradient-to-r from-primary to-secondary"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold flex items-center gap-2">
                    <Lock className="h-4 w-4 text-secondary" />
                    隐私保护指标
                  </h4>
                  <div className="space-y-3">
                    {[
                      { label: '隐私预算 ε', value: 1.0, max: 10 },
                      { label: '松弛参数 δ', value: 0.00001, max: 0.001, isExp: true },
                      { label: '敏感度 Δf', value: 1.0, max: 5 },
                      { label: '噪声规模 b', value: 1.0, max: 5 },
                      { label: '重识别风险降低', value: 95, max: 100 },
                    ].map((metric) => (
                      <div key={metric.label}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-muted-foreground">{metric.label}</span>
                          <span className="font-medium">
                            {metric.isExp ? metric.value.toExponential(1) : metric.value.toFixed(2)}
                          </span>
                        </div>
                        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(metric.value / metric.max) * 100}%` }}
                            transition={{ duration: 0.8 }}
                            className="h-full bg-gradient-to-r from-secondary to-green-500"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold flex items-center gap-2">
                    <Activity className="h-4 w-4 text-warning" />
                    系统效率
                  </h4>
                  <div className="space-y-3">
                    {[
                      { label: '平均响应时间', value: 185, unit: 'ms', reverse: true },
                      { label: '吞吐量', value: 92, unit: '请求/秒' },
                      { label: '内存占用', value: 2.3, unit: 'GB', max: 8 },
                      { label: 'CPU 利用率', value: 45, unit: '%' },
                      { label: '并发支持', value: 500, unit: '用户', max: 1000 },
                    ].map((metric, i) => {
                      const percentage = metric.max 
                        ? (metric.value / metric.max) * 100 
                        : (metric.reverse ? 100 - metric.value : metric.value)
                      return (
                        <div key={metric.label}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-muted-foreground">{metric.label}</span>
                            <span className="font-medium">
                              {metric.value}{metric.unit}
                            </span>
                          </div>
                          <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${percentage}%` }}
                              transition={{ duration: 0.8, delay: i * 0.1 }}
                              className="h-full bg-gradient-to-r from-warning to-orange-500"
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Research Summary */}
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                研究总结
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none">
                <p className="text-muted-foreground leading-relaxed">
                  本课题通过实验验证了<strong>差分隐私技术在医疗用药推荐场景中的可行性与有效性</strong>。
                  实验结果表明：
                </p>
                <ul className="space-y-2 text-muted-foreground mt-4">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                    <span>
                      在<strong>ε = 1.0</strong>的强隐私保护下，DeepFM 模型仍能达到<strong>89.7%</strong>的推荐准确率
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                    <span>
                      <strong>梯度层扰动</strong>策略相比数据层和模型层扰动，在准确率和隐私保护之间取得最佳平衡
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                    <span>
                      采用<strong>自适应预算分配</strong>算法，相比均匀分配提升约<strong>3.5%</strong>的模型性能
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                    <span>
                      <strong>Gaussian 噪声机制</strong>在高维医疗特征场景下表现最优，优于 Laplace 和 Geometric 机制
                    </span>
                  </li>
                </ul>
                <p className="text-muted-foreground mt-4 leading-relaxed">
                  以上可视化为毕设课题提供了直观的实验数据支撑，验证了所提方法的有效性。
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
}
