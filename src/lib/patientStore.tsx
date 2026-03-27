import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useAuth } from './authStore'
import { api, getErrorMessage } from './api'

export type PatientGender = '男' | '女' | '未知'

export interface Patient {
  id: string
  name: string
  age: number
  gender: PatientGender
  height: number
  weight: number
  allergies: string[]
  chronicDiseases: string[]
  currentMedications: string[]
  medicalHistory: string
  createdAt: string
}

type PatientDraft = Omit<Patient, 'id' | 'createdAt'>

type PatientStoreState = {
  patients: Patient[]
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
  addPatient: (patient: PatientDraft) => Promise<Patient>
  updatePatient: (id: string, updates: Partial<Omit<Patient, 'id' | 'createdAt'>>) => Promise<void>
  deletePatient: (id: string) => Promise<void>
}

type BackendPatient = {
  id: number
  name: string
  age: number
  gender: 'MALE' | 'FEMALE' | 'UNKNOWN'
  height: number
  weight: number
  allergies: string[]
  chronicDiseases: string[]
  currentMedications: string[]
  medicalHistory: string | null
  createdAt: string
}

type BackendPatientRequest = {
  name: string
  age: number
  gender: 'MALE' | 'FEMALE' | 'UNKNOWN'
  height: number
  weight: number
  allergies: string[]
  chronicDiseases: string[]
  currentMedications: string[]
  medicalHistory: string
}

const PatientStoreContext = createContext<PatientStoreState | null>(null)

function toFrontendGender(gender: BackendPatient['gender']): PatientGender {
  if (gender === 'FEMALE') return '女'
  if (gender === 'UNKNOWN') return '未知'
  return '男'
}

function toBackendGender(gender: PatientGender): BackendPatient['gender'] {
  if (gender === '女') return 'FEMALE'
  if (gender === '未知') return 'UNKNOWN'
  return 'MALE'
}

function normalizePatient(patient: BackendPatient): Patient {
  return {
    id: String(patient.id),
    name: patient.name,
    age: patient.age,
    gender: toFrontendGender(patient.gender),
    height: patient.height,
    weight: patient.weight,
    allergies: patient.allergies ?? [],
    chronicDiseases: patient.chronicDiseases ?? [],
    currentMedications: patient.currentMedications ?? [],
    medicalHistory: patient.medicalHistory ?? '',
    createdAt: patient.createdAt ? patient.createdAt.split('T')[0] : '',
  }
}

function toRequest(patient: Partial<PatientDraft>): BackendPatientRequest {
  return {
    name: patient.name?.trim() ?? '',
    age: patient.age ?? 0,
    gender: toBackendGender(patient.gender ?? '男'),
    height: patient.height ?? 0,
    weight: patient.weight ?? 0,
    allergies: (patient.allergies ?? []).map((item) => item.trim()).filter(Boolean),
    chronicDiseases: (patient.chronicDiseases ?? []).map((item) => item.trim()).filter(Boolean),
    currentMedications: (patient.currentMedications ?? []).map((item) => item.trim()).filter(Boolean),
    medicalHistory: patient.medicalHistory?.trim() ?? '',
  }
}

export function PatientStoreProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitializing, user } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!isAuthenticated || user?.role !== 'admin') {
      setPatients([])
      setError(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const data = await api.get<BackendPatient[]>('/api/patients')
      setPatients(data.map(normalizePatient))
      setError(null)
    } catch (err) {
      setPatients([])
      setError(getErrorMessage(err, '患者档案加载失败'))
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, user?.role])

  useEffect(() => {
    if (isInitializing) return
    void refresh()
  }, [isInitializing, refresh])

  const addPatient = useCallback<PatientStoreState['addPatient']>(async (patient) => {
    const created = await api.post<BackendPatient>('/api/patients', toRequest(patient))
    const nextPatient = normalizePatient(created)
    setPatients((prev) => [...prev, nextPatient])
    setError(null)
    return nextPatient
  }, [])

  const updatePatient = useCallback<PatientStoreState['updatePatient']>(async (id, updates) => {
    const current = patients.find((item) => item.id === id)
    if (!current) {
      throw new Error('未找到对应患者记录')
    }

    const updated = await api.put<BackendPatient>(`/api/patients/${id}`, toRequest({ ...current, ...updates }))
    const nextPatient = normalizePatient(updated)
    setPatients((prev) => prev.map((item) => (item.id === id ? nextPatient : item)))
    setError(null)
  }, [patients])

  const deletePatient = useCallback<PatientStoreState['deletePatient']>(async (id) => {
    await api.delete<void>(`/api/patients/${id}`)
    setPatients((prev) => prev.filter((item) => item.id !== id))
    setError(null)
  }, [])

  const value = useMemo<PatientStoreState>(
    () => ({ patients, isLoading, error, refresh, addPatient, updatePatient, deletePatient }),
    [addPatient, deletePatient, error, isLoading, patients, refresh, updatePatient]
  )

  return (
    <PatientStoreContext.Provider value={value}>
      {children}
    </PatientStoreContext.Provider>
  )
}

export function usePatientStore() {
  const ctx = useContext(PatientStoreContext)
  if (!ctx) throw new Error('usePatientStore must be used within PatientStoreProvider')
  return ctx
}

export function calcBMI(weight: number, height: number) {
  if (!height || height <= 0) return 0
  return weight / Math.pow(height / 100, 2)
}

export function bmiLabel(bmi: number): { label: string; color: string } {
  if (bmi < 18.5) return { label: '偏轻', color: 'text-blue-600 dark:text-blue-400' }
  if (bmi < 24) return { label: '正常', color: 'text-green-600 dark:text-green-400' }
  if (bmi < 28) return { label: '偏重', color: 'text-yellow-600 dark:text-yellow-400' }
  return { label: '肥胖', color: 'text-red-600 dark:text-red-400' }
}
