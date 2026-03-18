import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type PatientGender = '男' | '女'

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

type PatientStoreState = {
  patients: Patient[]
  addPatient: (p: Omit<Patient, 'id' | 'createdAt'>) => Patient
  updatePatient: (id: string, updates: Partial<Omit<Patient, 'id'>>) => void
  deletePatient: (id: string) => void
}

const STORAGE_KEY = 'dp_med_demo_patients_v1'

const INITIAL_PATIENTS: Patient[] = [
  {
    id: 'p1',
    name: '张三',
    age: 45,
    gender: '男',
    height: 175,
    weight: 70,
    allergies: ['青霉素', '阿司匹林'],
    chronicDiseases: ['高血压', '糖尿病'],
    currentMedications: ['二甲双胍', '氨氯地平'],
    medicalHistory: '2 型糖尿病史 5 年，高血压史 3 年',
    createdAt: '2024-01-15',
  },
  {
    id: 'p2',
    name: '李四',
    age: 62,
    gender: '女',
    height: 160,
    weight: 58,
    allergies: ['磺胺类'],
    chronicDiseases: ['冠心病'],
    currentMedications: ['阿司匹林肠溶片', '阿托伐他汀'],
    medicalHistory: '冠心病史 8 年，PCI 术后 3 年',
    createdAt: '2024-02-20',
  },
  {
    id: 'p3',
    name: '王五',
    age: 58,
    gender: '男',
    height: 172,
    weight: 80,
    allergies: [],
    chronicDiseases: ['高脂血症', '高血压', '2 型糖尿病'],
    currentMedications: ['阿托伐他汀', '缬沙坦'],
    medicalHistory: '高脂血症史 6 年，高血压史 4 年，近 1 年诊断 2 型糖尿病',
    createdAt: '2024-03-10',
  },
]

function safeParse(json: string | null): Patient[] | null {
  if (!json) return null
  try {
    const parsed = JSON.parse(json)
    return Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

const PatientStoreContext = createContext<PatientStoreState | null>(null)

export function PatientStoreProvider({ children }: { children: React.ReactNode }) {
  const [patients, setPatients] = useState<Patient[]>(INITIAL_PATIENTS)

  // Load persisted data on mount
  useEffect(() => {
    const persisted = safeParse(localStorage.getItem(STORAGE_KEY))
    if (persisted && persisted.length > 0) {
      setPatients(persisted)
    }
  }, [])

  // Persist on change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(patients))
  }, [patients])

  const addPatient = (p: Omit<Patient, 'id' | 'createdAt'>): Patient => {
    const newPatient: Patient = {
      ...p,
      id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
      createdAt: new Date().toISOString().split('T')[0],
    }
    setPatients((prev) => [...prev, newPatient])
    return newPatient
  }

  const updatePatient = (id: string, updates: Partial<Omit<Patient, 'id'>>) => {
    setPatients((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ...updates } : p))
    )
  }

  const deletePatient = (id: string) => {
    setPatients((prev) => prev.filter((p) => p.id !== id))
  }

  const value = useMemo<PatientStoreState>(
    () => ({ patients, addPatient, updatePatient, deletePatient }),
    [patients]
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

/** 计算 BMI */
export function calcBMI(weight: number, height: number) {
  if (!height || height <= 0) return 0
  return weight / Math.pow(height / 100, 2)
}

/** BMI 分类 */
export function bmiLabel(bmi: number): { label: string; color: string } {
  if (bmi < 18.5) return { label: '偏轻', color: 'text-blue-600 dark:text-blue-400' }
  if (bmi < 24) return { label: '正常', color: 'text-green-600 dark:text-green-400' }
  if (bmi < 28) return { label: '偏重', color: 'text-yellow-600 dark:text-yellow-400' }
  return { label: '肥胖', color: 'text-red-600 dark:text-red-400' }
}
