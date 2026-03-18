import { useMemo, useState, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  Users,
  Activity,
  Trash2,
  Brain,
  Play,
  CheckCircle2,
  User as UserIcon,
  Lock,
  Unlock,
  TrendingUp,
  Pill,
  Filter,
  RefreshCw,
  BarChart3,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { usePrivacyStore, formatEventType } from '@/lib/privacyStore'
import { useAuth } from '@/lib/authStore'
import { usePatientStore } from '@/lib/patientStore'

interface DemoUser {
  id: string
  username: string
  role: '管理员' | '普通用户'
  status: 'active' | 'disabled'
  lastLogin: string
}

const DEMO_USERS: DemoUser[] = [
  { id: 'u1', username: 'admin', role: '管理员', status: 'active', lastLogin: '2024-03-18 09:32' },
  { id: 'u2', username: 'user', role: '普通用户', status: 'active', lastLogin: '2024-03-18 10:15' },
]

interface TrainingPoint {
  epoch: number
  loss: number
  accuracy: number
  epsilonSpent: number
}

type LedgerFilter = 'all' | 'recommendation_inference' | 'training_epoch'

export default function AdminDashboard() {
  const { user } = useAuth()
  const { config, events, budget, addEvent, clearEvents } = usePrivacyStore()
  const { patients } = usePatientStore()

  // 用户管理状态
  const [userStatuses, setUserStatuses] = useState<Record<string, 'active' | 'disabled'>>({
    u1: 'active',
    u2: 'active',
  })

  // 模型训练状态
  const [isTraining, setIsTraining] = useState(false)
  const [trainingProgress, setTrainingProgress] = useState(0)
  const [trainingHistory, setTrainingHistory] = useState<TrainingPoint[]>([])
  const trainingRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 账本过滤
  const [ledgerFilter, setLedgerFilter] = useState<LedgerFilter>('all')

  // 系统概览统计
  const overviewStats = useMemo(() => {
    const todayInferences = events.filter(
      (e) => e.type === 'recommendation_inference' &&
        new Date(e.ts).toDateString() === new Date().toDateString()
    ).length
    const trainingEpochs = events.filter((e) => e.type === 'training_epoch').length
    return {
      patientCount: patients.length,
      drugCount: 6,
      todayInferences,
      trainingEpochs,
      modelAccuracy: trainingHistory.length > 0
        ? trainingHistory[trainingHistory.length - 1].accuracy.toFixed(1)
        : '89.7',
    }
  }, [events, patients, trainingHistory])

  // 启动模型训练模拟
  const handleStartTraining = () => {
    if (isTraining) return
    setIsTraining(true)
    setTrainingProgress(0)
    setTrainingHistory([])

    const totalEpochs = 10
    let epoch = 0

    const runEpoch = () => {
      epoch++
      // 模拟训练曲线：loss 下降，accuracy 上升
      const t = epoch / totalEpochs
      const loss = parseFloat((1.8 * Math.exp(-3 * t) + 0.15 + (Math.random() - 0.5) * 0.04).toFixed(4))
      const accuracy = parseFloat((60 + 28 * (1 - Math.exp(-4 * t)) + (Math.random() - 0.5) * 1.5).toFixed(2))
      const epsilonPerEpoch = parseFloat((config.epsilon / totalEpochs).toFixed(4))

      // 消耗隐私预算
      addEvent({
        type: 'training_epoch',
        epsilonSpent: Math.min(epsilonPerEpoch, Math.max(0, budget.remaining)),
        note: `Epoch ${epoch}/${totalEpochs}，loss=${loss}，acc=${accuracy}%`,
      })

      setTrainingHistory((prev) => [
        ...prev,
        { epoch, loss, accuracy, epsilonSpent: epsilonPerEpoch },
      ])
      setTrainingProgress(Math.round((epoch / totalEpochs) * 100))

      if (epoch < totalEpochs) {
        trainingRef.current = setTimeout(runEpoch, 600)
      } else {
        setIsTraining(false)
      }
    }

    trainingRef.current = setTimeout(runEpoch, 300)
  }

  // 过滤后的账本事件
  const filteredEvents = useMemo(() => {
    if (ledgerFilter === 'all') return events.slice(0, 30)
    return events.filter((e) => e.type === ledgerFilter).slice(0, 30)
  }, [events, ledgerFilter])

  const toggleUserStatus = (id: string) => {
    setUserStatuses((prev) => ({
      ...prev,
      [id]: prev[id] === 'active' ? 'disabled' : 'active',
    }))
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-2">
          后台管理
        </h1>
        <p className="text-muted-foreground">
          系统监控、用户管理、模型训练模拟与隐私预算审计
        </p>
      </div>

      {/* 管理员信息 */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
        <CardContent className="pt-6 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md">
              <UserIcon className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="font-semibold text-lg">{user?.username}</div>
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs">管理员</span>
                <span>· 已登录</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-wrap text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              系统运行正常
            </div>
            <div>隐私预算剩余：<span className="font-semibold text-secondary">{budget.remaining.toFixed(2)}</span></div>
          </div>
        </CardContent>
      </Card>

      {/* ===== 区块 1：系统概览 ===== */}
      <section>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          系统概览
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { icon: Users, label: '患者总数', value: `${overviewStats.patientCount} 人`, color: 'from-blue-500 to-cyan-500' },
            { icon: Pill, label: '药物种类', value: `${overviewStats.drugCount} 种`, color: 'from-purple-500 to-pink-500' },
            { icon: Activity, label: '今日推荐次数', value: `${overviewStats.todayInferences} 次`, color: 'from-green-500 to-emerald-500' },
            { icon: Brain, label: '训练轮次', value: `${overviewStats.trainingEpochs} epoch`, color: 'from-orange-500 to-red-500' },
            { icon: TrendingUp, label: '模型准确率', value: `${overviewStats.modelAccuracy}%`, color: 'from-primary to-secondary' },
          ].map((s, idx) => {
            const Icon = s.icon
            return (
              <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.06 }}>
                <Card className="border-border/40 bg-card/50 backdrop-blur hover:shadow-lg transition-all duration-300">
                  <CardContent className="pt-5 pb-4">
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center mb-3 shadow-md`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="text-2xl font-bold mb-1 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                      {s.value}
                    </div>
                    <div className="text-xs text-muted-foreground">{s.label}</div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </section>

      {/* ===== 区块 2：用户管理 ===== */}
      <section>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          用户管理
        </h2>
        <Card className="border-border/40 bg-card/50 backdrop-blur">
          <CardHeader>
            <CardDescription>演示用户列表（后端接入后可对接真实用户系统）</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted/60">
                  <tr className="text-left">
                    <th className="p-3 font-medium">账号</th>
                    <th className="p-3 font-medium">角色</th>
                    <th className="p-3 font-medium">最近登录</th>
                    <th className="p-3 font-medium">状态</th>
                    <th className="p-3 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {DEMO_USERS.map((u) => {
                    const status = userStatuses[u.id] ?? u.status
                    return (
                      <tr key={u.id} className="border-t border-border hover:bg-muted/20 transition-colors">
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                              <UserIcon className="h-4 w-4 text-white" />
                            </div>
                            <span className="font-medium">{u.username}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            u.role === '管理员'
                              ? 'bg-primary/10 text-primary'
                              : 'bg-secondary/10 text-secondary'
                          }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="p-3 text-muted-foreground">{u.lastLogin}</td>
                        <td className="p-3">
                          <span className={`flex items-center gap-1.5 w-fit px-2 py-1 rounded-full text-xs font-medium ${
                            status === 'active'
                              ? 'bg-green-100 dark:bg-green-950/40 text-green-700 dark:text-green-300'
                              : 'bg-red-100 dark:bg-red-950/40 text-red-600 dark:text-red-400'
                          }`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${status === 'active' ? 'bg-green-500' : 'bg-red-500'}`} />
                            {status === 'active' ? '正常' : '已禁用'}
                          </span>
                        </td>
                        <td className="p-3">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1.5 text-xs"
                            onClick={() => toggleUserStatus(u.id)}
                          >
                            {status === 'active'
                              ? <><Lock className="h-3.5 w-3.5" />禁用</>
                              : <><Unlock className="h-3.5 w-3.5" />启用</>
                            }
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              注：禁用/启用为前端 demo 状态，不影响实际登录功能，后端接入后可扩展为真实权限控制。
            </p>
          </CardContent>
        </Card>
      </section>

      {/* ===== 区块 3：模型训练模拟 ===== */}
      <section>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          模型训练模拟
        </h2>
        <div className="grid lg:grid-cols-2 gap-6">
          {/* 训练控制面板 */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base">训练控制</CardTitle>
              <CardDescription>
                模拟 DeepFM 模型在差分隐私约束下的训练过程（10 个 epoch）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-3 rounded-lg bg-background border border-border">
                  <div className="text-xs text-muted-foreground">当前 ε（每 epoch）</div>
                  <div className="font-semibold text-primary">{(config.epsilon / 10).toFixed(4)}</div>
                </div>
                <div className="p-3 rounded-lg bg-background border border-border">
                  <div className="text-xs text-muted-foreground">噪声机制</div>
                  <div className="font-semibold capitalize">{config.noiseMechanism}</div>
                </div>
                <div className="p-3 rounded-lg bg-background border border-border">
                  <div className="text-xs text-muted-foreground">注入阶段</div>
                  <div className="font-semibold">{config.applicationStage === 'data' ? '数据层' : config.applicationStage === 'gradient' ? '梯度层' : '模型层'}</div>
                </div>
                <div className="p-3 rounded-lg bg-background border border-border">
                  <div className="text-xs text-muted-foreground">剩余预算</div>
                  <div className="font-semibold text-secondary">ε = {budget.remaining.toFixed(2)}</div>
                </div>
              </div>

              {/* 进度条 */}
              {(isTraining || trainingHistory.length > 0) && (
                <div>
                  <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                    <span>训练进度</span>
                    <span>{trainingProgress}%</span>
                  </div>
                  <div className="w-full h-3 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                      animate={{ width: `${trainingProgress}%` }}
                      transition={{ duration: 0.4 }}
                    />
                  </div>
                </div>
              )}

              {/* 最新训练状态 */}
              {trainingHistory.length > 0 && (
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="p-2 rounded-lg bg-primary/5 border border-primary/20">
                    <div className="text-xs text-muted-foreground">当前 Epoch</div>
                    <div className="font-bold text-primary">{trainingHistory[trainingHistory.length - 1].epoch}/10</div>
                  </div>
                  <div className="p-2 rounded-lg bg-secondary/5 border border-secondary/20">
                    <div className="text-xs text-muted-foreground">Loss</div>
                    <div className="font-bold text-secondary">{trainingHistory[trainingHistory.length - 1].loss.toFixed(4)}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                    <div className="text-xs text-muted-foreground">Accuracy</div>
                    <div className="font-bold text-green-600 dark:text-green-400">{trainingHistory[trainingHistory.length - 1].accuracy.toFixed(1)}%</div>
                  </div>
                </div>
              )}

              {!isTraining && trainingHistory.length > 0 && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <span className="text-sm text-green-700 dark:text-green-300">训练完成！最终准确率 {trainingHistory[trainingHistory.length - 1].accuracy.toFixed(1)}%</span>
                </div>
              )}

              <div className="flex gap-3">
                <Button
                  onClick={handleStartTraining}
                  disabled={isTraining || budget.remaining <= 0}
                  className="flex-1 gap-2"
                  size="lg"
                >
                  {isTraining ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      训练中...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4" />
                      启动训练
                    </>
                  )}
                </Button>
                {trainingHistory.length > 0 && !isTraining && (
                  <Button variant="outline" onClick={() => { setTrainingHistory([]); setTrainingProgress(0) }}>
                    清除历史
                  </Button>
                )}
              </div>
              {budget.remaining <= 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  隐私预算已耗尽，无法继续训练。请在「隐私配置」中重置预算或增加总预算。
                </p>
              )}
            </CardContent>
          </Card>

          {/* 训练曲线图 */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base">训练曲线</CardTitle>
              <CardDescription>Loss 下降与准确率提升（DP-SGD 约束下）</CardDescription>
            </CardHeader>
            <CardContent>
              {trainingHistory.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[260px] text-muted-foreground">
                  <Brain className="h-12 w-12 mb-3 opacity-30" />
                  <p className="text-sm">点击「启动训练」后展示实时曲线</p>
                </div>
              ) : (
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trainingHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="epoch"
                        label={{ value: 'Epoch', position: 'insideBottom', offset: -4 }}
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        yAxisId="left"
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fontSize: 11 }}
                        label={{ value: 'Loss', angle: -90, position: 'insideLeft', fontSize: 11 }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        domain={[50, 100]}
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fontSize: 11 }}
                        label={{ value: 'Acc %', angle: 90, position: 'insideRight', fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '12px' }} />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="loss"
                        name="Loss"
                        stroke="hsl(var(--destructive))"
                        strokeWidth={2.5}
                        dot={{ r: 4 }}
                        isAnimationActive={false}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="accuracy"
                        name="Accuracy (%)"
                        stroke="hsl(var(--secondary))"
                        strokeWidth={2.5}
                        dot={{ r: 4 }}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {trainingHistory.length > 0 && (
                <div className="mt-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
                  <p className="text-xs text-blue-700 dark:text-blue-400">
                    本次训练共消耗隐私预算 ε = {(config.epsilon / 10 * trainingHistory.length).toFixed(4)}，
                    基于差分隐私 SGD（DP-SGD）算法在梯度更新时注入高斯/Laplace 噪声，确保训练数据隐私安全。
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ===== 区块 4：隐私预算账本 ===== */}
      <section>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          隐私预算账本
        </h2>
        <Card className="border-border/40 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <CardTitle className="text-base">账本记录（最近 30 条）</CardTitle>
                <CardDescription>
                  每次推荐推理或训练操作均自动记录 ε 消耗
                </CardDescription>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">类型：</span>
                  {(['all', 'recommendation_inference', 'training_epoch'] as LedgerFilter[]).map((f) => (
                    <button
                      key={f}
                      onClick={() => setLedgerFilter(f)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                        ledgerFilter === f
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      }`}
                    >
                      {f === 'all' ? '全部' : f === 'recommendation_inference' ? '推荐推理' : '训练轮次'}
                    </button>
                  ))}
                </div>
                <Button variant="outline" size="sm" className="gap-2 h-8" onClick={clearEvents}>
                  <Trash2 className="h-3.5 w-3.5" />
                  重置账本
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 预算汇总 */}
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="p-3 rounded-lg bg-background border border-border text-center">
                <div className="text-xs text-muted-foreground mb-1">总预算</div>
                <div className="font-bold text-lg">{config.privacyBudget.toFixed(1)}</div>
              </div>
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-center">
                <div className="text-xs text-muted-foreground mb-1">已消耗</div>
                <div className="font-bold text-lg text-red-600 dark:text-red-400">{budget.spent.toFixed(2)}</div>
              </div>
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 text-center">
                <div className="text-xs text-muted-foreground mb-1">剩余</div>
                <div className="font-bold text-lg text-green-600 dark:text-green-400">{budget.remaining.toFixed(2)}</div>
              </div>
            </div>

            {/* 进度条 */}
            <div>
              <div className="w-full h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-destructive transition-all duration-500 rounded-full"
                  style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>已消耗 {config.privacyBudget > 0 ? ((budget.spent / config.privacyBudget) * 100).toFixed(1) : 0}%</span>
                <span>ε_total = {config.privacyBudget.toFixed(1)}</span>
              </div>
            </div>

            {/* 账本表格 */}
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted/60">
                  <tr className="text-left">
                    <th className="p-3 font-medium">时间</th>
                    <th className="p-3 font-medium">类型</th>
                    <th className="p-3 font-medium">消耗 ε</th>
                    <th className="p-3 font-medium">备注</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.map((e) => (
                    <tr key={e.id} className="border-t border-border hover:bg-muted/20 transition-colors">
                      <td className="p-3 text-muted-foreground whitespace-nowrap">
                        {new Date(e.ts).toLocaleString()}
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          e.type === 'recommendation_inference'
                            ? 'bg-primary/10 text-primary'
                            : 'bg-secondary/10 text-secondary'
                        }`}>
                          {formatEventType(e.type)}
                        </span>
                      </td>
                      <td className="p-3 font-semibold text-primary">+ε {e.epsilonSpent.toFixed(4)}</td>
                      <td className="p-3 text-muted-foreground text-xs max-w-[200px] truncate">{e.note ?? '—'}</td>
                    </tr>
                  ))}
                  {filteredEvents.length === 0 && (
                    <tr>
                      <td className="p-4 text-muted-foreground text-center" colSpan={4}>
                        暂无记录。去「用药推荐」触发推理或在上方启动训练即可看到记录。
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
