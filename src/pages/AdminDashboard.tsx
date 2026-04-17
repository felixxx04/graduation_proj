import { useCallback, useEffect, useMemo, useState } from 'react'
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

const CHART_TOOLTIP_STYLE = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '3px',
  fontSize: '11px',
}

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
    void Promise.all([loadUsers(), loadDashboard(), loadTraining(), refreshPrivacy()])
  }, [loadDashboard, loadTraining, loadUsers, refreshPrivacy, user?.role])

  const selectedRun = useMemo(() => {
    if (!selectedTrainingId) return trainingRuns[0] ?? null
    return trainingRuns.find((run) => run.id === selectedTrainingId) ?? trainingRuns[0] ?? null
  }, [selectedTrainingId, trainingRuns])

  const trainingSeries = useMemo(
    () => (selectedRun?.epochs ?? []).map((item) => ({ epoch: item.epochIndex, loss: item.loss, accuracy: item.accuracy, epsilonSpent: item.epsilonSpent })),
    [selectedRun]
  )

  const filteredEvents = useMemo(() => {
    if (ledgerFilter === 'all') return events.slice(0, 30)
    return events.filter((item) => item.type === ledgerFilter).slice(0, 30)
  }, [events, ledgerFilter])

  const todayInferences = useMemo(() => {
    return events.filter(
      (event) => event.type === 'recommendation_inference' && new Date(event.ts).toDateString() === new Date().toDateString()
    ).length
  }, [events])

  const toggleUserStatus = async (target: AdminUserItem) => {
    setActionLoading(true)
    setActionError(null)
    try {
      const nextStatus = target.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
      const updated = await api.patch<AdminUserItem>(`/api/admin/users/${target.id}/status`, { status: nextStatus })
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
      const run = await api.post<TrainingRunItem>('/api/admin/training/start', { epochs: Math.max(1, Math.min(startEpochs, 50)) })
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
    <div className="space-y-8">
      {/* Page Header */}
      <section className="border-l-4 border-l-primary bg-card px-6 py-8">
        <div className="flex items-start gap-4">
          <div className="hidden md:flex h-10 w-10 items-center justify-center rounded-standard bg-primary flex-shrink-0">
            <Shield className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="flex-1">
            <h1 className="text-ia-tile font-display font-bold text-foreground mb-2">后台管理</h1>
            <p className="text-ia-body text-muted-foreground max-w-2xl">系统监控、用户管理、训练任务与隐私预算审计</p>
          </div>
        </div>
      </section>

      <Card hover="none" className="border-primary/20">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-standard bg-primary">
              <UserIcon className="h-4 w-4 text-primary-foreground" />
            </div>
            <div>
              <div className="font-heading font-semibold text-ia-body">{user?.username ?? '管理员'}</div>
              <div className="flex items-center gap-2 text-ia-label text-muted-foreground">
                <span className="ia-badge ia-badge-primary">管理员</span>
                <span>已登录</span>
              </div>
            </div>
          </div>
          <div className="text-ia-caption text-muted-foreground">隐私预算剩余：<span className="font-heading font-semibold text-secondary">{budget.remaining.toFixed(2)}</span></div>
        </CardContent>
      </Card>

      {(dashboardError || usersError || trainingError || actionError) && (
        <div className="rounded-standard border border-destructive/30 bg-destructive/6 p-2.5 text-ia-caption text-destructive">
          {dashboardError || usersError || trainingError || actionError}
        </div>
      )}

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-ia-card-title font-heading font-bold">
          <BarChart3 className="h-4 w-4 text-primary" />
          系统总览
        </h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {[
            { icon: Users, label: '患者总数', value: `${dashboard?.patientCount ?? 0}`, dataColor: 'ia-data-1' },
            { icon: Pill, label: '系统用户', value: `${dashboard?.userCount ?? 0}`, dataColor: 'ia-data-2' },
            { icon: Activity, label: '今日推理', value: `${todayInferences}`, dataColor: 'ia-data-3' },
            { icon: Brain, label: '账本事件', value: `${dashboard?.eventCount ?? 0}`, dataColor: 'ia-data-4' },
            { icon: TrendingUp, label: '推荐总数', value: `${dashboard?.recommendationCount ?? 0}`, dataColor: 'ia-data-5' },
          ].map((item) => {
            const Icon = item.icon
            return (
              <Card key={item.label} hover="border">
                <CardContent className="pb-3 pt-4">
                  <div className={`mb-2 flex h-8 w-8 items-center justify-center rounded-standard bg-${item.dataColor}/10`}>
                    <Icon className={`h-4 w-4 text-${item.dataColor}`} />
                  </div>
                  <div className="text-xl font-heading font-bold">{item.value}</div>
                  <div className="text-ia-label text-muted-foreground">{item.label}</div>
                </CardContent>
              </Card>
            )
          })}
        </div>
        <div className="mt-2 text-ia-label text-muted-foreground">
          已消耗 ε：{dashboard?.spentEpsilon.toFixed(3) ?? '0.000'} · 剩余 ε：{dashboard?.remainingBudget.toFixed(3) ?? '0.000'}
          {(loadingDashboard || loadingUsers || loadingTraining) && <span> · 同步中...</span>}
        </div>
      </section>

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-ia-card-title font-heading font-bold">
          <Users className="h-4 w-4 text-primary" />
          用户管理
        </h2>
        <Card hover="none">
          <CardContent className="pt-4">
            <div className="overflow-x-auto rounded-standard border border-ia-border">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>账号</th>
                    <th>角色</th>
                    <th>最近登录</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((item) => (
                    <tr key={item.id}>
                      <td className="font-heading font-semibold">{item.username}</td>
                      <td>{item.role === 'admin' ? '管理员' : '普通用户'}</td>
                      <td className="text-muted-foreground">{item.lastLoginAt ? new Date(item.lastLoginAt).toLocaleString() : '暂无'}</td>
                      <td>
                        <span className={item.status === 'ACTIVE' ? 'ia-badge ia-badge-success' : 'ia-badge ia-badge-danger'}>
                          {item.status === 'ACTIVE' ? '正常' : '禁用'}
                        </span>
                      </td>
                      <td>
                        <Button variant="outline" size="sm" className="h-7 gap-1.5 text-ia-label cursor-pointer" disabled={actionLoading} onClick={() => void toggleUserStatus(item)}>
                          {item.status === 'ACTIVE' ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                          {item.status === 'ACTIVE' ? '禁用' : '启用'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && !loadingUsers && (
                    <tr><td className="text-center text-muted-foreground" colSpan={5}>暂无用户数据</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-ia-card-title font-heading font-bold">
          <Brain className="h-4 w-4 text-primary" />
          模型训练
        </h2>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card hover="none">
            <CardHeader>
              <CardTitle className="text-base">训练控制</CardTitle>
              <CardDescription>调用后端训练接口并记录每个 epoch 的指标和隐私预算消耗</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-2 text-ia-caption">
                <div className="rounded-standard border border-ia-border bg-card p-2.5">
                  <div className="text-ia-label text-muted-foreground">当前机制</div>
                  <div className="font-heading font-semibold capitalize">{config.noiseMechanism}</div>
                </div>
                <div className="rounded-standard border border-ia-border bg-card p-2.5">
                  <div className="text-ia-label text-muted-foreground">注入阶段</div>
                  <div className="font-heading font-semibold">{config.applicationStage}</div>
                </div>
                <div className="rounded-standard border border-ia-border bg-card p-2.5">
                  <div className="text-ia-label text-muted-foreground">每轮预算(估算)</div>
                  <div className="font-heading font-semibold text-primary">{(config.epsilon / Math.max(startEpochs, 1)).toFixed(4)}</div>
                </div>
                <div className="rounded-standard border border-ia-border bg-card p-2.5">
                  <div className="text-ia-label text-muted-foreground">预算剩余</div>
                  <div className="font-heading font-semibold text-secondary">{budget.remaining.toFixed(2)}</div>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-ia-caption font-heading font-semibold">训练轮次 (1-50)</label>
                <input type="number" min={1} max={50} value={startEpochs} onChange={(event) => setStartEpochs(Number(event.target.value) || 1)} className="flex h-10 w-full rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary" />
              </div>

              <div className="flex gap-2">
                <Button size="lg" className="flex-1 gap-2 cursor-pointer" disabled={actionLoading || budget.remaining <= 0} onClick={() => void handleStartTraining()}>
                  {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  启动训练
                </Button>
                <Button variant="outline" onClick={() => void loadTraining()} disabled={loadingTraining} className="cursor-pointer">刷新历史</Button>
              </div>

              {trainingRuns.length > 0 && (
                <div className="space-y-1.5">
                  <label className="text-ia-caption font-heading font-semibold">选择训练任务</label>
                  <select value={selectedRun?.id ?? ''} onChange={(event) => setSelectedTrainingId(Number(event.target.value))} className="flex h-10 w-full rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary">
                    {trainingRuns.map((run) => (
                      <option key={run.id} value={run.id}>#{run.id} · {run.status} · {new Date(run.startedAt).toLocaleString()}</option>
                    ))}
                  </select>
                </div>
              )}
            </CardContent>
          </Card>

          <Card hover="none">
            <CardHeader>
              <CardTitle className="text-base">训练曲线</CardTitle>
              <CardDescription>展示所选训练任务的 loss 与 accuracy 变化</CardDescription>
            </CardHeader>
            <CardContent>
              {trainingSeries.length === 0 ? (
                <div className="flex h-[240px] flex-col items-center justify-center text-muted-foreground">
                  <Brain className="mb-3 h-10 w-10 opacity-30" />
                  <p className="text-ia-caption">暂无训练数据，启动训练后可查看曲线</p>
                </div>
              ) : (
                <div className="h-[240px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trainingSeries}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="epoch" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} />
                      <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} />
                      <YAxis yAxisId="right" orientation="right" domain={[50, 100]} stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} />
                      <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                      <Legend wrapperStyle={{ fontSize: '11px' }} />
                      <Line yAxisId="left" type="monotone" dataKey="loss" name="Loss" stroke="hsl(var(--destructive))" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                      <Line yAxisId="right" type="monotone" dataKey="accuracy" name="Accuracy (%)" stroke="hsl(var(--secondary))" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <section>
        <h2 className="mb-3 flex items-center gap-2 text-ia-card-title font-heading font-bold">
          <Shield className="h-4 w-4 text-primary" />
          隐私预算账本
        </h2>
        <Card hover="none">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base">账本记录（最近 30 条）</CardTitle>
                <CardDescription>自动记录推荐与训练产生的隐私预算消耗</CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1">
                  <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                  {(['all', 'recommendation_inference', 'training_epoch'] as LedgerFilter[]).map((item) => (
                    <button
                      key={item}
                      onClick={() => setLedgerFilter(item)}
                      className={`rounded-standard px-2 py-1 text-ia-label font-heading font-semibold transition-colors duration-150 cursor-pointer ${
                        ledgerFilter === item ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      }`}
                    >
                      {item === 'all' ? '全部' : item === 'recommendation_inference' ? '推荐推理' : '训练轮次'}
                    </button>
                  ))}
                </div>
                <Button variant="outline" size="sm" className="h-7 gap-1.5 cursor-pointer" onClick={() => void handleClearLedger()} disabled={actionLoading}>
                  <Trash2 className="h-3 w-3" />
                  重置账本
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-2 text-ia-caption">
              <div className="rounded-standard border border-ia-border bg-card p-2.5 text-center">
                <div className="text-ia-label text-muted-foreground mb-0.5">总预算</div>
                <div className="text-ia-body font-heading font-bold">{config.privacyBudget.toFixed(1)}</div>
              </div>
              <div className="rounded-standard border border-destructive/30 bg-destructive/6 p-2.5 text-center">
                <div className="text-ia-label text-muted-foreground mb-0.5">已消耗</div>
                <div className="text-ia-body font-heading font-bold text-destructive">{budget.spent.toFixed(2)}</div>
              </div>
              <div className="rounded-standard border border-ia-data-3/30 bg-ia-data-3/6 p-2.5 text-center">
                <div className="text-ia-label text-muted-foreground mb-0.5">剩余</div>
                <div className="text-ia-body font-heading font-bold text-ia-data-3">{budget.remaining.toFixed(2)}</div>
              </div>
            </div>

            <div>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }}
                />
              </div>
              <div className="mt-1 flex justify-between text-ia-label text-muted-foreground">
                <span>已消耗 {config.privacyBudget > 0 ? ((budget.spent / config.privacyBudget) * 100).toFixed(1) : 0}%</span>
                <span>ε_total = {config.privacyBudget.toFixed(1)}</span>
              </div>
            </div>

            <div className="overflow-x-auto rounded-standard border border-ia-border">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>类型</th>
                    <th>消耗 ε</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.map((event) => (
                    <tr key={event.id}>
                      <td className="whitespace-nowrap text-muted-foreground">{new Date(event.ts).toLocaleString()}</td>
                      <td><span className={event.type === 'recommendation_inference' ? 'ia-badge ia-badge-primary' : 'ia-badge ia-badge-info'}>{formatEventType(event.type)}</span></td>
                      <td className="font-heading font-semibold text-primary">+ε {event.epsilonSpent.toFixed(4)}</td>
                      <td className="max-w-[200px] truncate text-muted-foreground">{event.note ?? '-'}</td>
                    </tr>
                  ))}
                  {filteredEvents.length === 0 && (
                    <tr><td className="text-center text-muted-foreground" colSpan={4}>暂无账本记录</td></tr>
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
