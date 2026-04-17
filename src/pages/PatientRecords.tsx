import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
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
import { PatientCardSkeleton, StatCardSkeleton } from '@/components/ui/skeleton'
import { TextExpander } from '@/components/ui/text-expander'
import { AgeDistributionChart } from '@/components/charts/AgeDistributionChart'
import { DiseaseDistributionChart } from '@/components/charts/DiseaseDistributionChart'

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
  const addFormRef = useRef<HTMLDivElement>(null)
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const scrollToForm = () => {
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current)
    scrollTimeoutRef.current = setTimeout(() => {
      addFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 300)
  }

  const stats = useMemo(() => {
    if (!patients.length) return { total: 0, avgAge: 0, diseaseCount: 0, avgBMI: 0 }
    const avgAge = Math.round(patients.reduce((sum, patient) => sum + patient.age, 0) / patients.length)
    const allDiseases = new Set(patients.flatMap((patient) => patient.chronicDiseases))
    const bmis = patients.map((patient) => calcBMI(patient.weight, patient.height)).filter((value) => value > 0)
    const avgBMI = bmis.length > 0 ? Math.round((bmis.reduce((sum, value) => sum + value, 0) / bmis.length) * 10) / 10 : 0
    return { total: patients.length, avgAge, diseaseCount: allDiseases.size, avgBMI }
  }, [patients])

  const ageDistribution = useMemo(() => {
    const groups = { '30-40岁': 0, '40-50岁': 0, '50-60岁': 0, '60-70岁': 0, '70岁以上': 0 }
    patients.forEach((p) => {
      if (p.age < 40) groups['30-40岁']++
      else if (p.age < 50) groups['40-50岁']++
      else if (p.age < 60) groups['50-60岁']++
      else if (p.age < 70) groups['60-70岁']++
      else groups['70岁以上']++
    })
    return [
      { name: '30-40岁', value: groups['30-40岁'], color: 'hsl(var(--ia-data-1))' },
      { name: '40-50岁', value: groups['40-50岁'], color: 'hsl(var(--ia-data-2))' },
      { name: '50-60岁', value: groups['50-60岁'], color: 'hsl(var(--ia-data-3))' },
      { name: '60-70岁', value: groups['60-70岁'], color: 'hsl(var(--ia-data-4))' },
      { name: '70岁以上', value: groups['70岁以上'], color: 'hsl(var(--ia-data-5))' },
    ].filter((d) => d.value > 0)
  }, [patients])

  const diseaseDistribution = useMemo(() => {
    const diseaseCount: Record<string, number> = {}
    patients.forEach((p) => { p.chronicDiseases.forEach((d) => { diseaseCount[d] = (diseaseCount[d] || 0) + 1 }) })
    return Object.entries(diseaseCount).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, 8)
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
    if (sortKey === key) { setSortDir((current) => (current === 'asc' ? 'desc' : 'asc')) }
    else { setSortKey(key); setSortDir('asc') }
  }

  const resetForm = () => { setFormData(INITIAL_FORM); setShowAddForm(false); setEditingId(null); setPageError(null) }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true); setPageError(null)
    const payload = {
      name: formData.name.trim(), age: Number.parseInt(formData.age, 10) || 0, gender: formData.gender,
      height: Number.parseFloat(formData.height) || 0, weight: Number.parseFloat(formData.weight) || 0,
      allergies: splitList(formData.allergies), chronicDiseases: splitList(formData.chronicDiseases),
      currentMedications: splitList(formData.currentMedications), medicalHistory: formData.medicalHistory.trim(),
    }
    try {
      if (editingId) { await updatePatient(editingId, payload) } else { await addPatient(payload) }
      resetForm()
    } catch (submitError) { setPageError(getErrorMessage(submitError, '保存患者信息失败')) }
    finally { setSubmitting(false) }
  }

  const handleEdit = (patient: Patient) => {
    setFormData({
      name: patient.name, age: String(patient.age), gender: patient.gender, height: String(patient.height),
      weight: String(patient.weight), allergies: patient.allergies.join(', '), chronicDiseases: patient.chronicDiseases.join(', '),
      currentMedications: patient.currentMedications.join(', '), medicalHistory: patient.medicalHistory,
    })
    setEditingId(patient.id); setShowAddForm(true); setPageError(null)
  }

  const handleDelete = async (id: string) => {
    setPageError(null)
    try { await deletePatient(id) } catch (deleteError) { setPageError(getErrorMessage(deleteError, '删除患者失败')) }
  }

  const handleGoToRecommendation = (patient: Patient) => {
    navigate('/recommendation', {
      state: { prefill: { age: String(patient.age), gender: patient.gender, diseases: patient.chronicDiseases.join('，'), symptoms: patient.medicalHistory, allergies: patient.allergies.join('，'), currentMedications: patient.currentMedications.join('，') } },
    })
  }

  const SortButton = ({ label, keyName }: { label: string; keyName: SortKey }) => (
    <button
      onClick={() => toggleSort(keyName)}
      className={`flex items-center gap-1 rounded-standard px-2.5 py-1 text-ia-label font-heading font-semibold transition-colors duration-150 cursor-pointer ${
        sortKey === keyName ? 'bg-primary/8 text-primary border border-primary/20' : 'text-muted-foreground hover:bg-muted border border-transparent'
      }`}
    >
      {label}
      <ArrowUpDown className="h-3 w-3" />
      {sortKey === keyName && <span className="text-ia-label">{sortDir === 'asc' ? '↑' : '↓'}</span>}
    </button>
  )

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <section className="border-l-4 border-l-primary bg-card px-6 py-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="hidden md:flex h-10 w-10 items-center justify-center rounded-standard bg-primary flex-shrink-0">
              <Users className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-ia-tile font-display font-bold text-foreground mb-2">患者档案管理</h1>
              <p className="text-ia-body text-muted-foreground max-w-2xl">管理患者健康信息，为个性化用药推荐提供数据支持</p>
            </div>
          </div>
          <Button onClick={() => { resetForm(); setShowAddForm(true); scrollToForm() }} className="gap-2 cursor-pointer" size="sm">
            <Plus className="h-4 w-4" />
            添加患者
          </Button>
        </div>
      </section>

      {(error || pageError) && (
        <div className="rounded-standard border border-destructive/30 bg-destructive/6 p-2.5 text-ia-caption text-destructive">
          {pageError || error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
          : [
              { icon: Users, label: '患者总数', value: `${stats.total}`, dataColor: 'ia-data-1' },
              { icon: Calendar, label: '平均年龄', value: `${stats.avgAge}`, dataColor: 'ia-data-2' },
              { icon: Heart, label: '慢病种类', value: `${stats.diseaseCount}`, dataColor: 'ia-data-5' },
              { icon: Scale, label: '平均 BMI', value: stats.avgBMI.toFixed(1), dataColor: 'ia-data-3' },
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

      {/* Charts */}
      {!isLoading && patients.length > 0 && (
        <div className="grid gap-5 md:grid-cols-2">
          <AgeDistributionChart data={ageDistribution} />
          <DiseaseDistributionChart data={diseaseDistribution} />
        </div>
      )}

      <Card hover="none">
        <CardContent className="space-y-2.5 pt-4">
          <Input
            placeholder="搜索患者姓名..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            icon={<Search className="h-4 w-4" />}
          />
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-ia-label text-muted-foreground">排序：</span>
            <SortButton label="姓名" keyName="name" />
            <SortButton label="年龄" keyName="age" />
            <SortButton label="建档日期" keyName="createdAt" />
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {showAddForm && (
          <div className="animate-fade-in">
            <Card ref={addFormRef} hover="none" className="border-primary/20 scroll-mt-[60px]">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{editingId ? '编辑患者信息' : '添加新患者'}</CardTitle>
                    <CardDescription>填写患者基本信息和健康档案</CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={resetForm} className="cursor-pointer">
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit}>
                <CardContent className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="p-name" className="text-ia-caption font-heading font-semibold">姓名 *</Label>
                      <Input id="p-name" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} required />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-age" className="text-ia-caption font-heading font-semibold">年龄 *</Label>
                      <Input id="p-age" type="number" value={formData.age} onChange={(event) => setFormData({ ...formData, age: event.target.value })} required />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-gender" className="text-ia-caption font-heading font-semibold">性别 *</Label>
                      <select id="p-gender" value={formData.gender} onChange={(event) => setFormData({ ...formData, gender: event.target.value as PatientGender })} className="flex h-10 w-full rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary">
                        <option value="男">男</option>
                        <option value="女">女</option>
                        <option value="未知">未知</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <Label htmlFor="p-height" className="text-ia-caption font-heading font-semibold">身高 (cm)</Label>
                        <Input id="p-height" type="number" value={formData.height} onChange={(event) => setFormData({ ...formData, height: event.target.value })} />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="p-weight" className="text-ia-caption font-heading font-semibold">体重 (kg)</Label>
                        <Input id="p-weight" type="number" value={formData.weight} onChange={(event) => setFormData({ ...formData, weight: event.target.value })} />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1.5"><Label htmlFor="p-allergies" className="text-ia-caption font-heading font-semibold">过敏史（逗号分隔）</Label><Input id="p-allergies" value={formData.allergies} onChange={(event) => setFormData({ ...formData, allergies: event.target.value })} /></div>
                  <div className="space-y-1.5"><Label htmlFor="p-diseases" className="text-ia-caption font-heading font-semibold">慢病（逗号分隔）</Label><Input id="p-diseases" value={formData.chronicDiseases} onChange={(event) => setFormData({ ...formData, chronicDiseases: event.target.value })} /></div>
                  <div className="space-y-1.5"><Label htmlFor="p-meds" className="text-ia-caption font-heading font-semibold">当前用药（逗号分隔）</Label><Input id="p-meds" value={formData.currentMedications} onChange={(event) => setFormData({ ...formData, currentMedications: event.target.value })} /></div>
                  <div className="space-y-1.5">
                    <Label htmlFor="p-history" className="text-ia-caption font-heading font-semibold">既往病史</Label>
                    <textarea id="p-history" value={formData.medicalHistory} onChange={(event) => setFormData({ ...formData, medicalHistory: event.target.value })} className="flex min-h-[80px] w-full resize-none rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary" />
                  </div>

                  <div className="flex gap-2 pt-3">
                    <Button type="submit" className="gap-2 cursor-pointer" disabled={submitting}>
                      <Save className="h-4 w-4" />
                      {submitting ? '提交中...' : editingId ? '保存修改' : '添加患者'}
                    </Button>
                    <Button type="button" variant="outline" onClick={resetForm} className="cursor-pointer">取消</Button>
                  </div>
                </CardContent>
              </form>
            </Card>
          </div>
        )}
      </AnimatePresence>

      <div className="space-y-2.5">
        <div className="px-1 text-ia-label text-muted-foreground">
          {isLoading ? '加载中...' : `共 ${filteredPatients.length} 条记录${searchTerm ? `（搜索：${searchTerm}）` : ''}`}
        </div>

        {isLoading && (
          <div className="space-y-2.5">
            {Array.from({ length: 5 }).map((_, i) => (<PatientCardSkeleton key={i} />))}
          </div>
        )}

        <AnimatePresence>
          {!isLoading && filteredPatients.map((patient) => {
            const bmi = calcBMI(patient.weight, patient.height)
            const { label: bmiText, color: bmiColor } = bmiLabel(bmi)
            const isExpanded = expandedPatient === patient.id

            return (
              <div key={patient.id} className="animate-fade-in">
                <Card hover="border" className="overflow-hidden">
                  <CardContent className="p-0">
                    <div className="cursor-pointer p-4" onClick={() => setExpandedPatient(isExpanded ? null : patient.id)}>
                      <div className="flex items-start justify-between">
                        <div className="flex min-w-0 flex-1 items-start gap-3">
                          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-standard bg-primary">
                            <User className="h-5 w-5 text-primary-foreground" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="mb-1.5 flex flex-wrap items-center gap-2">
                              <h3 className="font-heading font-semibold text-ia-card-title">{patient.name}</h3>
                              <span className="ia-badge ia-badge-primary">{patient.gender} · {patient.age} 岁</span>
                            </div>
                            <div className="mb-2 flex flex-wrap gap-3 text-ia-caption text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Activity className="h-3.5 w-3.5" />
                                <span className={bmiColor}>BMI: {bmi.toFixed(1)} ({bmiText})</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <AlertTriangle className="h-3.5 w-3.5 text-ia-data-4" />
                                <span>{patient.allergies.length} 项过敏</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3.5 w-3.5" />
                                <span>建档：{patient.createdAt}</span>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {patient.chronicDiseases.slice(0, 3).map((disease) => (
                                <span key={disease} className="ia-badge ia-badge-info">{disease}</span>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="ml-2 flex flex-shrink-0 items-center gap-0.5">
                          <Button variant="ghost" size="sm" className="gap-1 text-ia-label text-primary hover:text-primary cursor-pointer" onClick={(event) => { event.stopPropagation(); handleGoToRecommendation(patient) }}>
                            <Stethoscope className="h-3.5 w-3.5" />
                            推荐
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 cursor-pointer" onClick={(event) => { event.stopPropagation(); handleEdit(patient) }}><Edit2 className="h-3.5 w-3.5" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 cursor-pointer" onClick={(event) => { event.stopPropagation(); void handleDelete(patient.id) }}><Trash2 className="h-3.5 w-3.5" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 cursor-pointer">{isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}</Button>
                        </div>
                      </div>
                    </div>

                    <AnimatePresence>
                      {isExpanded && (
                        <div className="animate-fade-in overflow-hidden border-t border-ia-border">
                          <div className="px-4 pb-4">
                            <div className="mt-4 grid gap-4 md:grid-cols-3">
                              <div>
                                <h4 className="mb-2 text-ia-caption font-heading font-semibold text-primary">当前用药</h4>
                                <div className="space-y-1.5">
                                  {patient.currentMedications.length > 0 ? patient.currentMedications.map((medication) => (
                                    <div key={medication} className="flex items-center gap-2 rounded-standard bg-primary/4 border border-primary/10 p-2">
                                      <div className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                                      <span className="text-ia-caption">{medication}</span>
                                    </div>
                                  )) : <p className="text-ia-label text-muted-foreground">无</p>}
                                </div>
                              </div>
                              <div>
                                <h4 className="mb-2 text-ia-caption font-heading font-semibold text-secondary">过敏史</h4>
                                <div className="space-y-1.5">
                                  {patient.allergies.length > 0 ? patient.allergies.map((allergy) => (
                                    <div key={allergy} className="flex items-center gap-2 rounded-standard border border-destructive/20 bg-destructive/4 p-2">
                                      <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-destructive" />
                                      <span className="text-ia-caption text-destructive">{allergy}</span>
                                    </div>
                                  )) : <p className="text-ia-label text-muted-foreground">无过敏史</p>}
                                </div>
                              </div>
                              <div>
                                <h4 className="mb-2 text-ia-caption font-heading font-semibold">体格信息</h4>
                                <div className="space-y-1.5 text-ia-caption">
                                  <div className="flex justify-between rounded-standard bg-muted p-2">
                                    <span className="text-muted-foreground">身高</span>
                                    <span className="font-heading font-semibold">{patient.height} cm</span>
                                  </div>
                                  <div className="flex justify-between rounded-standard bg-muted p-2">
                                    <span className="text-muted-foreground">体重</span>
                                    <span className="font-heading font-semibold">{patient.weight} kg</span>
                                  </div>
                                  <div className="flex justify-between rounded-standard bg-muted p-2">
                                    <span className="text-muted-foreground">BMI</span>
                                    <span className={`font-heading font-semibold ${bmiColor}`}>{bmi.toFixed(1)} ({bmiText})</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                            {patient.medicalHistory && (
                              <div className="mt-4 border-t border-ia-border pt-4">
                                <h4 className="mb-1.5 text-ia-caption font-heading font-semibold">既往病史</h4>
                                <TextExpander text={patient.medicalHistory} maxLines={3} />
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </AnimatePresence>
                  </CardContent>
                </Card>
              </div>
            )
          })}
        </AnimatePresence>

        {!isLoading && filteredPatients.length === 0 && (
          <Card hover="none" className="border-dashed">
            <CardContent className="py-10 text-center">
              <User className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <h3 className="mb-1.5 font-heading font-semibold text-ia-card-title">未找到患者</h3>
              <p className="text-ia-caption text-muted-foreground">{searchTerm ? '请尝试其他搜索关键词' : '点击上方按钮添加第一位患者'}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
