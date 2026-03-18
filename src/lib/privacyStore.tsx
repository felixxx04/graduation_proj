import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { PrivacyConfig, PrivacyLedgerEvent, PrivacyEventType } from './privacy'
import { clampNumber, sumEpsilon } from './privacy'

type PrivacyStoreState = {
  config: PrivacyConfig
  setConfig: (next: PrivacyConfig) => void
  events: PrivacyLedgerEvent[]
  addEvent: (e: Omit<PrivacyLedgerEvent, 'id' | 'ts'>) => PrivacyLedgerEvent
  clearEvents: () => void
  budget: {
    total: number
    spent: number
    remaining: number
  }
}

const DEFAULT_CONFIG: PrivacyConfig = {
  epsilon: 1.0,
  delta: 0.00001,
  sensitivity: 1.0,
  noiseMechanism: 'laplace',
  applicationStage: 'gradient',
  privacyBudget: 10.0,
}

const STORAGE_KEY = 'dp_med_demo_privacy_store_v1'

type Persisted = {
  config: PrivacyConfig
  events: PrivacyLedgerEvent[]
}

function safeParse(json: string | null): Persisted | null {
  if (!json) return null
  try {
    return JSON.parse(json) as Persisted
  } catch {
    return null
  }
}

function normalizeConfig(input: PrivacyConfig): PrivacyConfig {
  return {
    epsilon: clampNumber(input.epsilon, 0.000001, 50),
    delta: clampNumber(input.delta, 1e-12, 0.5),
    sensitivity: clampNumber(input.sensitivity, 0.000001, 100),
    noiseMechanism: input.noiseMechanism,
    applicationStage: input.applicationStage,
    privacyBudget: clampNumber(input.privacyBudget, 0, 1_000),
  }
}

const PrivacyStoreContext = createContext<PrivacyStoreState | null>(null)

export function PrivacyStoreProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfigState] = useState<PrivacyConfig>(DEFAULT_CONFIG)
  const [events, setEvents] = useState<PrivacyLedgerEvent[]>([])

  useEffect(() => {
    const persisted = safeParse(localStorage.getItem(STORAGE_KEY))
    if (!persisted) return
    if (persisted.config) setConfigState(normalizeConfig({ ...DEFAULT_CONFIG, ...persisted.config }))
    if (Array.isArray(persisted.events)) setEvents(persisted.events)
  }, [])

  useEffect(() => {
    const persisted: Persisted = { config, events }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted))
  }, [config, events])

  const budget = useMemo(() => {
    const spent = sumEpsilon(events)
    const total = Math.max(0, config.privacyBudget)
    const remaining = Math.max(0, total - spent)
    return { total, spent, remaining }
  }, [config.privacyBudget, events])

  const setConfig = (next: PrivacyConfig) => setConfigState(normalizeConfig(next))

  const addEvent = (e: Omit<PrivacyLedgerEvent, 'id' | 'ts'>) => {
    const evt: PrivacyLedgerEvent = {
      id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      ts: Date.now(),
      ...e,
    }
    setEvents((prev) => [evt, ...prev].slice(0, 200))
    return evt
  }

  const clearEvents = () => setEvents([])

  const value: PrivacyStoreState = {
    config,
    setConfig,
    events,
    addEvent,
    clearEvents,
    budget,
  }

  return <PrivacyStoreContext.Provider value={value}>{children}</PrivacyStoreContext.Provider>
}

export function usePrivacyStore() {
  const ctx = useContext(PrivacyStoreContext)
  if (!ctx) throw new Error('usePrivacyStore must be used within PrivacyStoreProvider')
  return ctx
}

export function formatEventType(t: PrivacyEventType) {
  if (t === 'recommendation_inference') return '推荐推理'
  if (t === 'training_epoch') return '训练轮次'
  return t
}

