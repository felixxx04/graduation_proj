import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  Users,
  Activity,
  Trash2,
  Brain,
  Play,
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
import { api, getErrorMessage } from '@/lib/api'

interface AdminUserItem {
  id: number
  username: string
  role: string
  status: 'ACTIVE' | 'DISABLED'
  lastLoginAt: string | null
}

interface TrainingEpochItem {
  epochIndex: number
  loss: number
  accuracy: number
  epsilonSpent: number
  createdAt: string
}

interface TrainingRunItem {
  id: number
  status: string
  totalEpochs: number
  epsilonPerEpoch: number
  startedAt: string
  finishedAt: string | null
  epochs: TrainingEpochItem[]
}

interface DashboardResponse {
  patientCount: number
  userCount: number
  recommendationCount: number
  eventCount: number
  spentEpsilon: number
  remainingBudget: number
}

type LedgerFilter = 'all' | 'recommendation_inference' | 'training_epoch'

export default function AdminDashboard() {
  const { user } = useAuth()
  const { config, events, budget, clearEvents, refresh: refreshPrivacy } = usePrivacyStore()

  const [users, setUsers] = useState<AdminUserItem[]>([])
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [trainingRuns, setTrainingRuns] = useState<TrainingRunItem[]>([])
  const [selectedTrainingId, setSelectedTrainingId] = useState<number | null>(null)
  const [startEpochs, setStartEpochs] = useState(10)

  const [loadingUsers, setLoadingUsers] = useState(false)
  const [loadingDashboard, setLoadingDashboard] = useState(false)
  const [loadingTraining, setLoadingTraining] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  const [usersError, setUsersError] = useState<string | null>(null)
  const [dashboardError, setDashboardError] = useState<string | null>(null)
  const [trainingError, setTrainingError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const [ledgerFilter, setLedgerFilter] = useState<LedgerFilter>('all')

  const loadUsers = useCallback(async () => {
    setLoadingUsers(true)
    try {
      const data = await api.get<AdminUserItem[]>('/api/admin/users')
      setUsers(data)
      setUsersError(null)
    } catch (error) {
      setUsersError(getErrorMessage(error, '用户列表加载失败'))
    } finally {
      setLoadingUsers(false)
    }
  }, [])

  const loadDashboard = useCallback(async () => {
    setLoadingDashboard(true)
    try {
      const data = await api.get<DashboardResponse>('/api/dashboard/visualization')
      setDashboard(data)
      setDashboardError(null)
    } catch (error) {
      setDashboardError(getErrorMessage(error, '系统概览加载失败'))
    } finally {
      setLoadingDashboard(false)
    }
  }, [])

  const loadTraining = useCallback(async () => {
    setLoadingTraining(true)
    try {
      const data = await api.get<TrainingRunItem[]>('/api/admin/training/history?limit=10')
      setTrainingRuns(data)
      if (data.length > 0) {
        setSelectedTrainingId((current) => current ?? data[0].id)
      } else {
        setSelectedTrainingId(null)
      }
      setTrainingError(null)
    } catch (error) {
      setTrainingError(getErrorMessage(error, '训练历史加载失败'))
    } finally {
      setLoadingTraining(false)
    }
  }, [])

  useEffect(() => {
    if (user?.role !== 'admin') return

    void Promise.all([
      loadUsers(),
      loadDashboard(),
      loadTraining(),
      refreshPrivacy(),
    ])
  }, [loadDashboard, loadTraining, loadUsers, refreshPrivacy, user?.role])

  const selectedRun = useMemo(() => {
    if (!selectedTrainingId) return trainingRuns[0] ?? null
    return trainingRuns.find((run) => run.id === selectedTrainingId) ?? trainingRuns[0] ?? null
  }, [selectedTrainingId, trainingRuns])

  const trainingSeries = useMemo(
    () =>
      (selectedRun?.epochs ?? []).map((item) => ({
        epoch: item.epochIndex,
        loss: item.loss,
        accuracy: item.accuracy,
        epsilonSpent: item.epsilonSpent,
      })),
    [selectedRun]
  )

  const filteredEvents = useMemo(() => {
    if (ledgerFilter === 'all') return events.slice(0, 30)
    return events.filter((item) => item.type === ledgerFilter).slice(0, 30)
  }, [events, ledgerFilter])

  const todayInferences = useMemo(() => {
    return events.filter(
      (event) =>
        event.type === 'recommendation_inference' &&
        new Date(event.ts).toDateString() === new Date().toDateString()
    ).length
  }, [events])

  const toggleUserStatus = async (target: AdminUserItem) => {
    setActionLoading(true)
    setActionError(null)
    try {
      const nextStatus = target.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
      const updated = await api.patch<AdminUserItem>(`/api/admin/users/${target.id}/status`, {
        status: nextStatus,
      })
      setUsers((prev) => prev.map((item) => (item.id === target.id ? updated : item)))
    } catch (error) {
      setActionError(getErrorMessage(error, '更新用户状态失败'))
    } finally {
      setActionLoading(false)
    }
  }

  const handleStartTraining = async () => {
    setActionLoading(true)
    setActionError(null)
    try {
      const run = await api.post<TrainingRunItem>('/api/admin/training/start', {
        epochs: Math.max(1, Math.min(startEpochs, 50)),
      })
      setTrainingRuns((prev) => [run, ...prev])
      setSelectedTrainingId(run.id)
      await Promise.all([refreshPrivacy(), loadDashboard()])
    } catch (error) {
      setActionError(getErrorMessage(error, '启动训练失败'))
    } finally {
      setActionLoading(false)
    }
  }

  const handleClearLedger = async () => {
    setActionLoading(true)
    setActionError(null)
    try {
      await clearEvents()
      await loadDashboard()
    } catch (error) {
      setActionError(getErrorMessage(error, '重置账本失败'))
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="space-y-10">
      {/* Hero Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden rounded-2xl"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-slate-800 via-slate-700 to-zinc-800" />
        <div className="absolute inset-0 bg-medical-dna opacity-20" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl" />

        <div className="relative z-10 px-8 py-10 md:px-12 md:py-14">
          <div className="flex items-start gap-5">
            <div className="hidden md:flex w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-sm items-center justify-center shadow-xl">
              <Shield className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-bold text-white mb-3 tracking-tight">
                后台管理
              </h1>
              <p className="text-white/60 text-lg max-w-2xl">
                系统监控、用户管理、训练任务与隐私预算审计
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-md">
              <UserIcon className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="text-lg font-semibold">{user?.username ?? '管理员'}</div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">管理员</span>
                <span>已登录</span>
              </div>
            </div>
          </div>
          <div className="text-sm text-muted-foreground">隐私预算剩余：<span className="font-semibold text-secondary">{budget.remaining.toFixed(2)}</span></div>
        </CardContent>
      </Card>

      {(dashboardError || usersError || trainingError || actionError) && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          {dashboardError || usersError || trainingError || actionError}
        </div>
      )}

      <section>
        <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
          <BarChart3 className="h-5 w-5 text-primary" />
          系统总览
        </h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          {[
            { icon: Users, label: '患者总数', value: `${dashboard?.patientCount ?? 0}`, color: 'from-blue-500 to-cyan-500' },
            { icon: Pill, label: '系统用户', value: `${dashboard?.userCount ?? 0}`, color: 'from-purple-500 to-pink-500' },
            { icon: Activity, label: '今日推理', value: `${todayInferences}`, color: 'from-green-500 to-emerald-500' },
            { icon: Brain, label: '账本事件', value: `${dashboard?.eventCount ?? 0}`, color: 'from-orange-500 to-red-500' },
            { icon: TrendingUp, label: '推荐总数', value: `${dashboard?.recommendationCount ?? 0}`, color: 'from-primary to-secondary' },
          ].map((item, index) => {
            const Icon = item.icon
            return (
              <motion.div key={item.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
                <Card className="border-border/40 bg-card/50 backdrop-blur">
                  <CardContent className="pb-4 pt-5">
                    <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${item.color} shadow-md`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="text-2xl font-bold">{item.value}</div>
                    <div className="text-xs text-muted-foreground">{item.label}</div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>
        <div className="mt-3 text-sm text-muted-foreground">
          已消耗 ε：{dashboard?.spentEpsilon.toFixed(3) ?? '0.000'} · 剩余 ε：{dashboard?.remainingBudget.toFixed(3) ?? '0.000'}
          {(loadingDashboard || loadingUsers || loadingTraining) && <span> · 同步中...</span>}
        </div>
      </section>

      <section>
        <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
          <Users className="h-5 w-5 text-primary" />
          用户管理
        </h2>
        <Card className="border-border/40 bg-card/50 backdrop-blur">
          <CardContent className="pt-6">
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
                  {users.map((item) => (
                    <tr key={item.id} className="border-t border-border hover:bg-muted/20">
                      <td className="p-3 font-medium">{item.username}</td>
                      <td className="p-3">{item.role === 'admin' ? '管理员' : '普通用户'}</td>
                      <td className="p-3 text-muted-foreground">
                        {item.lastLoginAt ? new Date(item.lastLoginAt).toLocaleString() : '暂无'}
                      </td>
                      <td className="p-3">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-medium ${
                            item.status === 'ACTIVE'
                              ? 'bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300'
                              : 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300'
                          }`}
                        >
                          {item.status === 'ACTIVE' ? '正常' : '禁用'}
                        </span>
                      </td>
                      <td className="p-3">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 gap-1.5"
                          disabled={actionLoading}
                          onClick={() => void toggleUserStatus(item)}
                        >
                          {item.status === 'ACTIVE' ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                          {item.status === 'ACTIVE' ? '禁用' : '启用'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && !loadingUsers && (
                    <tr>
                      <td className="p-4 text-center text-muted-foreground" colSpan={5}>
                        暂无用户数据
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
          <Brain className="h-5 w-5 text-primary" />
          模型训练
        </h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base">训练控制</CardTitle>
              <CardDescription>调用后端训练接口并记录每个 epoch 的指标和隐私预算消耗</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg border border-border bg-background p-3">
                  <div className="text-xs text-muted-foreground">当前机制</div>
                  <div className="font-semibold capitalize">{config.noiseMechanism}</div>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <div className="text-xs text-muted-foreground">注入阶段</div>
                  <div className="font-semibold">{config.applicationStage}</div>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <div className="text-xs text-muted-foreground">每轮预算(估算)</div>
                  <div className="font-semibold text-primary">{(config.epsilon / Math.max(startEpochs, 1)).toFixed(4)}</div>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <div className="text-xs text-muted-foreground">预算剩余</div>
                  <div className="font-semibold text-secondary">{budget.remaining.toFixed(2)}</div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">训练轮次 (1-50)</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={startEpochs}
                  onChange={(event) => setStartEpochs(Number(event.target.value) || 1)}
                  className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  size="lg"
                  className="flex-1 gap-2"
                  disabled={actionLoading || budget.remaining <= 0}
                  onClick={() => void handleStartTraining()}
                >
                  {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  启动训练
                </Button>
                <Button variant="outline" onClick={() => void loadTraining()} disabled={loadingTraining}>
                  刷新历史
                </Button>
              </div>

              {trainingRuns.length > 0 && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">选择训练任务</label>
                  <select
                    value={selectedRun?.id ?? ''}
                    onChange={(event) => setSelectedTrainingId(Number(event.target.value))}
                    className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  >
                    {trainingRuns.map((run) => (
                      <option key={run.id} value={run.id}>
                        #{run.id} · {run.status} · {new Date(run.startedAt).toLocaleString()}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base">训练曲线</CardTitle>
              <CardDescription>展示所选训练任务的 loss 与 accuracy 变化</CardDescription>
            </CardHeader>
            <CardContent>
              {trainingSeries.length === 0 ? (
                <div className="flex h-[260px] flex-col items-center justify-center text-muted-foreground">
                  <Brain className="mb-3 h-12 w-12 opacity-30" />
                  <p className="text-sm">暂无训练数据，启动训练后可查看曲线</p>
                </div>
              ) : (
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trainingSeries}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="epoch" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" domain={[50, 100]} stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '12px' }} />
                      <Line yAxisId="left" type="monotone" dataKey="loss" name="Loss" stroke="hsl(var(--destructive))" strokeWidth={2.5} dot={{ r: 4 }} isAnimationActive={false} />
                      <Line yAxisId="right" type="monotone" dataKey="accuracy" name="Accuracy (%)" stroke="hsl(var(--secondary))" strokeWidth={2.5} dot={{ r: 4 }} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <section>
        <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
          <Shield className="h-5 w-5 text-primary" />
          隐私预算账本
        </h2>
        <Card className="border-border/40 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base">账本记录（最近 30 条）</CardTitle>
                <CardDescription>自动记录推荐与训练产生的隐私预算消耗</CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  {(['all', 'recommendation_inference', 'training_epoch'] as LedgerFilter[]).map((item) => (
                    <button
                      key={item}
                      onClick={() => setLedgerFilter(item)}
                      className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                        ledgerFilter === item
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      }`}
                    >
                      {item === 'all' ? '全部' : item === 'recommendation_inference' ? '推荐推理' : '训练轮次'}
                    </button>
                  ))}
                </div>
                <Button variant="outline" size="sm" className="h-8 gap-2" onClick={() => void handleClearLedger()} disabled={actionLoading}>
                  <Trash2 className="h-3.5 w-3.5" />
                  重置账本
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-lg border border-border bg-background p-3 text-center">
                <div className="mb-1 text-xs text-muted-foreground">总预算</div>
                <div className="text-lg font-bold">{config.privacyBudget.toFixed(1)}</div>
              </div>
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-center dark:border-red-800 dark:bg-red-950/30">
                <div className="mb-1 text-xs text-muted-foreground">已消耗</div>
                <div className="text-lg font-bold text-red-600 dark:text-red-400">{budget.spent.toFixed(2)}</div>
              </div>
              <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-center dark:border-green-800 dark:bg-green-950/30">
                <div className="mb-1 text-xs text-muted-foreground">剩余</div>
                <div className="text-lg font-bold text-green-600 dark:text-green-400">{budget.remaining.toFixed(2)}</div>
              </div>
            </div>

            <div>
              <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-destructive transition-all duration-500"
                  style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }}
                />
              </div>
              <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                <span>已消耗 {config.privacyBudget > 0 ? ((budget.spent / config.privacyBudget) * 100).toFixed(1) : 0}%</span>
                <span>ε_total = {config.privacyBudget.toFixed(1)}</span>
              </div>
            </div>

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
                  {filteredEvents.map((event) => (
                    <tr key={event.id} className="border-t border-border hover:bg-muted/20">
                      <td className="whitespace-nowrap p-3 text-muted-foreground">{new Date(event.ts).toLocaleString()}</td>
                      <td className="p-3">
                        <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                          event.type === 'recommendation_inference'
                            ? 'bg-primary/10 text-primary'
                            : 'bg-secondary/10 text-secondary'
                        }`}>
                          {formatEventType(event.type)}
                        </span>
                      </td>
                      <td className="p-3 font-semibold text-primary">+ε {event.epsilonSpent.toFixed(4)}</td>
                      <td className="max-w-[220px] truncate p-3 text-xs text-muted-foreground">{event.note ?? '-'}</td>
                    </tr>
                  ))}
                  {filteredEvents.length === 0 && (
                    <tr>
                      <td className="p-4 text-center text-muted-foreground" colSpan={4}>
                        暂无账本记录
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
