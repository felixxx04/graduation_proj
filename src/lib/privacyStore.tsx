import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useAuth } from './authStore'
import { api, getErrorMessage } from './api'
import type { ApplicationStage, NoiseMechanism, PrivacyConfig, PrivacyEventType, PrivacyLedgerEvent } from './privacy'

const DEFAULT_CONFIG: PrivacyConfig = {
  epsilon: 1.0,
  delta: 0.00001,
  sensitivity: 0.2,  // sigmoid输出[0,1]的实证灵敏度，而非理论最大值1.0
  noiseMechanism: 'laplace',
  applicationStage: 'gradient',
  privacyBudget: 10.0,
}

type PrivacyBudget = {
  total: number
  spent: number
  remaining: number
}

type PrivacyStoreState = {
  config: PrivacyConfig
  setConfig: (next: PrivacyConfig) => Promise<void>
  events: PrivacyLedgerEvent[]
  clearEvents: () => Promise<void>
  refresh: () => Promise<void>
  budget: PrivacyBudget
  isLoading: boolean
  error: string | null
}

type BackendConfig = {
  id: number
  epsilon: number
  delta: number
  sensitivity: number
  noiseMechanism: string
  applicationStage: string
  privacyBudget: number
}

type BackendBudget = {
  total: number
  spent: number
  remaining: number
}

type BackendEvent = {
  id: number
  type: string
  epsilonSpent: number
  deltaSpent?: number | null
  note?: string | null
  createdAt: string
}

type BackendConfigWithBudget = {
  config: BackendConfig
  budget: BackendBudget
  recentEvents: BackendEvent[]
}

const DEFAULT_BUDGET: PrivacyBudget = {
  total: DEFAULT_CONFIG.privacyBudget,
  spent: 0,
  remaining: DEFAULT_CONFIG.privacyBudget,
}

const PrivacyStoreContext = createContext<PrivacyStoreState | null>(null)

function normalizeNoiseMechanism(value: string): NoiseMechanism {
  if (value === 'GAUSSIAN') return 'gaussian'
  if (value === 'GEOMETRIC') return 'geometric'
  return 'laplace'
}

function normalizeApplicationStage(value: string): ApplicationStage {
  if (value === 'DATA') return 'data'
  if (value === 'MODEL') return 'model'
  return 'gradient'
}

function normalizeEventType(value: string): PrivacyEventType {
  if (value === 'TRAINING_EPOCH') return 'training_epoch'
  return 'recommendation_inference'
}

function toBackendNoiseMechanism(value: NoiseMechanism) {
  if (value === 'gaussian') return 'GAUSSIAN'
  if (value === 'geometric') return 'GEOMETRIC'
  return 'LAPLACE'
}

function toBackendApplicationStage(value: ApplicationStage) {
  if (value === 'data') return 'DATA'
  if (value === 'model') return 'MODEL'
  return 'GRADIENT'
}

function normalizeConfig(config: BackendConfig): PrivacyConfig {
  return {
    epsilon: config.epsilon,
    delta: config.delta,
    sensitivity: config.sensitivity,
    noiseMechanism: normalizeNoiseMechanism(config.noiseMechanism),
    applicationStage: normalizeApplicationStage(config.applicationStage),
    privacyBudget: config.privacyBudget,
  }
}

function normalizeBudget(budget: BackendBudget): PrivacyBudget {
  return {
    total: budget.total,
    spent: budget.spent,
    remaining: budget.remaining,
  }
}

function normalizeEvent(event: BackendEvent): PrivacyLedgerEvent {
  const parsedTime = Date.parse(event.createdAt)
  return {
    id: String(event.id),
    ts: Number.isNaN(parsedTime) ? Date.now() : parsedTime,
    type: normalizeEventType(event.type),
    epsilonSpent: event.epsilonSpent,
    deltaSpent: event.deltaSpent ?? undefined,
    note: event.note ?? undefined,
  }
}

export function PrivacyStoreProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitializing } = useAuth()
  const [config, setConfigState] = useState<PrivacyConfig>(DEFAULT_CONFIG)
  const [events, setEvents] = useState<PrivacyLedgerEvent[]>([])
  const [budget, setBudget] = useState<PrivacyBudget>(DEFAULT_BUDGET)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setConfigState(DEFAULT_CONFIG)
      setEvents([])
      setBudget(DEFAULT_BUDGET)
      setError(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const [configData, eventData] = await Promise.all([
        api.get<BackendConfigWithBudget>('/api/privacy/config'),
        api.get<BackendEvent[]>('/api/privacy/events?limit=200'),
      ])

      setConfigState(normalizeConfig(configData.config))
      setBudget(normalizeBudget(configData.budget))
      setEvents(eventData.map(normalizeEvent))
      setError(null)
    } catch (err) {
      setError(getErrorMessage(err, '隐私配置加载失败'))
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (isInitializing) return
    void refresh()
  }, [isInitializing, refresh])

  const setConfig = useCallback<PrivacyStoreState['setConfig']>(async (next) => {
    await api.put<BackendConfig>('/api/privacy/config', {
      epsilon: next.epsilon,
      delta: next.delta,
      sensitivity: next.sensitivity,
      noiseMechanism: toBackendNoiseMechanism(next.noiseMechanism),
      applicationStage: toBackendApplicationStage(next.applicationStage),
      privacyBudget: next.privacyBudget,
    })
    await refresh()
  }, [refresh])

  const clearEvents = useCallback<PrivacyStoreState['clearEvents']>(async () => {
    await api.delete<void>('/api/privacy/events')
    setEvents([])
    setBudget({
      total: config.privacyBudget,
      spent: 0,
      remaining: config.privacyBudget,
    })
    setError(null)
  }, [config.privacyBudget])

  const value = useMemo<PrivacyStoreState>(
    () => ({
      config,
      setConfig,
      events,
      clearEvents,
      refresh,
      budget,
      isLoading,
      error,
    }),
    [budget, clearEvents, config, error, events, isLoading, refresh, setConfig]
  )

  return <PrivacyStoreContext.Provider value={value}>{children}</PrivacyStoreContext.Provider>
}

export function usePrivacyStore() {
  const ctx = useContext(PrivacyStoreContext)
  if (!ctx) throw new Error('usePrivacyStore must be used within PrivacyStoreProvider')
  return ctx
}

export function formatEventType(type: PrivacyEventType) {
  if (type === 'recommendation_inference') return '推荐推理'
  if (type === 'training_epoch') return '训练轮次'
  return type
}
