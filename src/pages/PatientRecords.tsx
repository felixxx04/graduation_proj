import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  User,
  Calendar,
  Activity,
  AlertTriangle,
  Save,
  X,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  Stethoscope,
  Users,
  Heart,
  Scale,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePatientStore, calcBMI, bmiLabel, type Patient, type PatientGender } from '@/lib/patientStore'
import { getErrorMessage } from '@/lib/api'

type SortKey = 'name' | 'age' | 'createdAt'
type SortDir = 'asc' | 'desc'

type FormState = {
  name: string
  age: string
  gender: PatientGender
  height: string
  weight: string
  allergies: string
  chronicDiseases: string
  currentMedications: string
  medicalHistory: string
}

const INITIAL_FORM: FormState = {
  name: '',
  age: '',
  gender: '男',
  height: '',
  weight: '',
  allergies: '',
  chronicDiseases: '',
  currentMedications: '',
  medicalHistory: '',
}

function splitList(value: string) {
  return value.split(/[,，、]/).map((item) => item.trim()).filter(Boolean)
}

export default function PatientRecords() {
  const { patients, addPatient, updatePatient, deletePatient, isLoading, error } = usePatientStore()
  const navigate = useNavigate()

  const [searchTerm, setSearchTerm] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('createdAt')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [expandedPatient, setExpandedPatient] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [formData, setFormData] = useState<FormState>(INITIAL_FORM)

  const stats = useMemo(() => {
    if (!patients.length) return { total: 0, avgAge: 0, diseaseCount: 0, avgBMI: 0 }
    const avgAge = Math.round(patients.reduce((sum, patient) => sum + patient.age, 0) / patients.length)
    const allDiseases = new Set(patients.flatMap((patient) => patient.chronicDiseases))
    const bmis = patients.map((patient) => calcBMI(patient.weight, patient.height)).filter((value) => value > 0)
    const avgBMI = bmis.length > 0 ? Math.round((bmis.reduce((sum, value) => sum + value, 0) / bmis.length) * 10) / 10 : 0
    return { total: patients.length, avgAge, diseaseCount: allDiseases.size, avgBMI }
  }, [patients])

  const filteredPatients = useMemo(() => {
    const term = searchTerm.toLowerCase().trim()
    let list = patients.filter((patient) => patient.name.toLowerCase().includes(term))

    list = [...list].sort((left, right) => {
      const leftValue = sortKey === 'name' ? left.name : sortKey === 'age' ? left.age : left.createdAt
      const rightValue = sortKey === 'name' ? right.name : sortKey === 'age' ? right.age : right.createdAt
      if (leftValue < rightValue) return sortDir === 'asc' ? -1 : 1
      if (leftValue > rightValue) return sortDir === 'asc' ? 1 : -1
      return 0
    })

    return list
  }, [patients, searchTerm, sortDir, sortKey])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((current) => (current === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const resetForm = () => {
    setFormData(INITIAL_FORM)
    setShowAddForm(false)
    setEditingId(null)
    setPageError(null)
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setPageError(null)

    const payload = {
      name: formData.name.trim(),
      age: Number.parseInt(formData.age, 10) || 0,
      gender: formData.gender,
      height: Number.parseFloat(formData.height) || 0,
      weight: Number.parseFloat(formData.weight) || 0,
      allergies: splitList(formData.allergies),
      chronicDiseases: splitList(formData.chronicDiseases),
      currentMedications: splitList(formData.currentMedications),
      medicalHistory: formData.medicalHistory.trim(),
    }

    try {
      if (editingId) {
        await updatePatient(editingId, payload)
      } else {
        await addPatient(payload)
      }
      resetForm()
    } catch (submitError) {
      setPageError(getErrorMessage(submitError, '保存患者信息失败'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleEdit = (patient: Patient) => {
    setFormData({
      name: patient.name,
      age: String(patient.age),
      gender: patient.gender,
      height: String(patient.height),
      weight: String(patient.weight),
      allergies: patient.allergies.join(', '),
      chronicDiseases: patient.chronicDiseases.join(', '),
      currentMedications: patient.currentMedications.join(', '),
      medicalHistory: patient.medicalHistory,
    })
    setEditingId(patient.id)
    setShowAddForm(true)
    setPageError(null)
  }

  const handleDelete = async (id: string) => {
    setPageError(null)
    try {
      await deletePatient(id)
    } catch (deleteError) {
      setPageError(getErrorMessage(deleteError, '删除患者失败'))
    }
  }

  const handleGoToRecommendation = (patient: Patient) => {
    navigate('/recommendation', {
      state: {
        prefill: {
          age: String(patient.age),
          gender: patient.gender,
          diseases: patient.chronicDiseases.join('，'),
          symptoms: patient.medicalHistory,
          allergies: patient.allergies.join('，'),
          currentMedications: patient.currentMedications.join('，'),
        },
      },
    })
  }

  const SortButton = ({ label, keyName }: { label: string; keyName: SortKey }) => (
    <button
      onClick={() => toggleSort(keyName)}
      className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
        sortKey === keyName ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      }`}
    >
      {label}
      <ArrowUpDown className="h-3.5 w-3.5" />
      {sortKey === keyName && <span className="text-xs">{sortDir === 'asc' ? '↑' : '↓'}</span>}
    </button>
  )

  return (
    <div className="space-y-8">
      <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="mb-2 bg-gradient-to-r from-primary to-secondary bg-clip-text text-3xl font-bold text-transparent">患者档案管理</h1>
          <p className="text-muted-foreground">管理患者健康信息，为个性化用药推荐提供数据支持</p>
        </div>
        <Button onClick={() => { resetForm(); setShowAddForm(true) }} className="gap-2 shadow-lg hover:shadow-xl">
          <Plus className="h-4 w-4" />
          添加患者
        </Button>
      </div>

      {(error || pageError) && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          {pageError || error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { icon: Users, label: '患者总数', value: `${stats.total}`, color: 'from-blue-500 to-cyan-500' },
          { icon: Calendar, label: '平均年龄', value: `${stats.avgAge}`, color: 'from-purple-500 to-pink-500' },
          { icon: Heart, label: '慢病种类', value: `${stats.diseaseCount}`, color: 'from-red-500 to-orange-500' },
          { icon: Scale, label: '平均 BMI', value: stats.avgBMI.toFixed(1), color: 'from-green-500 to-emerald-500' },
        ].map((item) => {
          const Icon = item.icon
          return (
            <Card key={item.label} className="border-border/40 bg-card/50 backdrop-blur">
              <CardContent className="pb-4 pt-5">
                <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${item.color} shadow-md`}>
                  <Icon className="h-5 w-5 text-white" />
                </div>
                <div className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-2xl font-bold text-transparent">{item.value}</div>
                <div className="mt-1 text-xs text-muted-foreground">{item.label}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card className="border-border/40 bg-card/50 backdrop-blur">
        <CardContent className="space-y-3 pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索患者姓名..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              className="h-12 pl-10"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">排序：</span>
            <SortButton label="姓名" keyName="name" />
            <SortButton label="年龄" keyName="age" />
            <SortButton label="建档日期" keyName="createdAt" />
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {showAddForm && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{editingId ? '编辑患者信息' : '添加新患者'}</CardTitle>
                    <CardDescription>填写患者基本信息和健康档案</CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={resetForm}>
                    <X className="h-5 w-5" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit}>
                <CardContent className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="p-name">姓名 *</Label>
                      <Input id="p-name" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="p-age">年龄 *</Label>
                      <Input id="p-age" type="number" value={formData.age} onChange={(event) => setFormData({ ...formData, age: event.target.value })} required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="p-gender">性别 *</Label>
                      <select
                        id="p-gender"
                        value={formData.gender}
                        onChange={(event) => setFormData({ ...formData, gender: event.target.value as PatientGender })}
                        className="flex h-11 w-full rounded-lg border border-input bg-background px-4 py-2 text-sm"
                      >
                        <option value="男">男</option>
                        <option value="女">女</option>
                        <option value="未知">未知</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="p-height">身高 (cm)</Label>
                        <Input id="p-height" type="number" value={formData.height} onChange={(event) => setFormData({ ...formData, height: event.target.value })} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="p-weight">体重 (kg)</Label>
                        <Input id="p-weight" type="number" value={formData.weight} onChange={(event) => setFormData({ ...formData, weight: event.target.value })} />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="p-allergies">过敏史（逗号分隔）</Label>
                    <Input id="p-allergies" value={formData.allergies} onChange={(event) => setFormData({ ...formData, allergies: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="p-diseases">慢病（逗号分隔）</Label>
                    <Input id="p-diseases" value={formData.chronicDiseases} onChange={(event) => setFormData({ ...formData, chronicDiseases: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="p-meds">当前用药（逗号分隔）</Label>
                    <Input id="p-meds" value={formData.currentMedications} onChange={(event) => setFormData({ ...formData, currentMedications: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="p-history">既往病史</Label>
                    <textarea
                      id="p-history"
                      value={formData.medicalHistory}
                      onChange={(event) => setFormData({ ...formData, medicalHistory: event.target.value })}
                      className="flex min-h-[100px] w-full resize-none rounded-lg border border-input bg-background px-4 py-2 text-sm"
                    />
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button type="submit" className="gap-2" disabled={submitting}>
                      <Save className="h-4 w-4" />
                      {submitting ? '提交中...' : editingId ? '保存修改' : '添加患者'}
                    </Button>
                    <Button type="button" variant="outline" onClick={resetForm}>取消</Button>
                  </div>
                </CardContent>
              </form>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-3">
        <div className="px-1 text-sm text-muted-foreground">
          {isLoading ? '加载中...' : `共 ${filteredPatients.length} 条记录${searchTerm ? `（搜索：${searchTerm}）` : ''}`}
        </div>

        <AnimatePresence>
          {!isLoading && filteredPatients.map((patient, index) => {
            const bmi = calcBMI(patient.weight, patient.height)
            const { label: bmiText, color: bmiColor } = bmiLabel(bmi)
            const isExpanded = expandedPatient === patient.id

            return (
              <motion.div key={patient.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ delay: index * 0.04 }}>
                <Card className="overflow-hidden border-border/40 bg-card/50 backdrop-blur hover:shadow-lg">
                  <CardContent className="p-0">
                    <div className="cursor-pointer p-6" onClick={() => setExpandedPatient(isExpanded ? null : patient.id)}>
                      <div className="flex items-start justify-between">
                        <div className="flex min-w-0 flex-1 items-start gap-4">
                          <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-md">
                            <User className="h-7 w-7 text-white" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="mb-2 flex flex-wrap items-center gap-3">
                              <h3 className="text-xl font-semibold">{patient.name}</h3>
                              <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">{patient.gender} · {patient.age} 岁</span>
                            </div>
                            <div className="mb-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Activity className="h-4 w-4" />
                                <span className={bmiColor}>BMI: {bmi.toFixed(1)} ({bmiText})</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                                <span>{patient.allergies.length} 项过敏</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Calendar className="h-4 w-4" />
                                <span>建档：{patient.createdAt}</span>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {patient.chronicDiseases.slice(0, 3).map((disease) => (
                                <span key={disease} className="rounded-full bg-secondary/10 px-3 py-1 text-xs font-medium text-secondary">{disease}</span>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="ml-3 flex flex-shrink-0 items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="gap-1.5 text-xs text-secondary hover:bg-secondary/10 hover:text-secondary"
                            onClick={(event) => { event.stopPropagation(); handleGoToRecommendation(patient) }}
                          >
                            <Stethoscope className="h-4 w-4" />
                            快速推荐
                          </Button>
                          <Button variant="ghost" size="icon" onClick={(event) => { event.stopPropagation(); handleEdit(patient) }}>
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={(event) => { event.stopPropagation(); void handleDelete(patient.id) }}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon">
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </div>
                      </div>
                    </div>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div key="detail" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden border-t border-border">
                          <div className="px-6 pb-6">
                            <div className="mt-6 grid gap-6 md:grid-cols-3">
                              <div>
                                <h4 className="mb-3 text-sm font-semibold text-primary">当前用药</h4>
                                <div className="space-y-2">
                                  {patient.currentMedications.length > 0 ? patient.currentMedications.map((medication) => (
                                    <div key={medication} className="flex items-center gap-2 rounded-lg bg-primary/5 p-2.5">
                                      <div className="h-2 w-2 flex-shrink-0 rounded-full bg-primary" />
                                      <span className="text-sm">{medication}</span>
                                    </div>
                                  )) : <p className="text-sm text-muted-foreground">无</p>}
                                </div>
                              </div>
                              <div>
                                <h4 className="mb-3 text-sm font-semibold text-secondary">过敏史</h4>
                                <div className="space-y-2">
                                  {patient.allergies.length > 0 ? patient.allergies.map((allergy) => (
                                    <div key={allergy} className="flex items-center gap-2 rounded-lg bg-red-50 p-2.5 dark:bg-red-950/30">
                                      <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-500" />
                                      <span className="text-sm text-red-600 dark:text-red-400">{allergy}</span>
                                    </div>
                                  )) : <p className="text-sm text-muted-foreground">无过敏史</p>}
                                </div>
                              </div>
                              <div>
                                <h4 className="mb-3 text-sm font-semibold">体格信息</h4>
                                <div className="space-y-2 text-sm">
                                  <div className="flex justify-between rounded-lg bg-muted/40 p-2">
                                    <span className="text-muted-foreground">身高</span>
                                    <span className="font-medium">{patient.height} cm</span>
                                  </div>
                                  <div className="flex justify-between rounded-lg bg-muted/40 p-2">
                                    <span className="text-muted-foreground">体重</span>
                                    <span className="font-medium">{patient.weight} kg</span>
                                  </div>
                                  <div className="flex justify-between rounded-lg bg-muted/40 p-2">
                                    <span className="text-muted-foreground">BMI</span>
                                    <span className={`font-semibold ${bmiColor}`}>{bmi.toFixed(1)} ({bmiText})</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                            {patient.medicalHistory && (
                              <div className="mt-5 border-t border-border pt-5">
                                <h4 className="mb-2 text-sm font-semibold">既往病史</h4>
                                <p className="text-sm leading-relaxed text-muted-foreground">{patient.medicalHistory}</p>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {!isLoading && filteredPatients.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="py-12 text-center">
              <User className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
              <h3 className="mb-2 text-lg font-semibold">未找到患者</h3>
              <p className="text-muted-foreground">{searchTerm ? '请尝试其他搜索关键词' : '点击上方按钮添加第一位患者'}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
