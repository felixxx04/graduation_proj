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

type SortKey = 'name' | 'age' | 'createdAt'
type SortDir = 'asc' | 'desc'

export default function PatientRecords() {
  const { patients, addPatient, updatePatient, deletePatient } = usePatientStore()
  const navigate = useNavigate()

  const [searchTerm, setSearchTerm] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('createdAt')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [expandedPatient, setExpandedPatient] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    age: '',
    gender: '男' as PatientGender,
    height: '',
    weight: '',
    allergies: '',
    chronicDiseases: '',
    currentMedications: '',
    medicalHistory: '',
  })

  // 统计指标
  const stats = useMemo(() => {
    if (!patients.length) return { total: 0, avgAge: 0, diseaseCount: 0, avgBMI: 0 }
    const avgAge = Math.round(patients.reduce((s, p) => s + p.age, 0) / patients.length)
    const allDiseases = new Set(patients.flatMap((p) => p.chronicDiseases))
    const bmis = patients
      .map((p) => calcBMI(p.weight, p.height))
      .filter((b) => b > 0)
    const avgBMI =
      bmis.length > 0 ? Math.round((bmis.reduce((s, b) => s + b, 0) / bmis.length) * 10) / 10 : 0
    return { total: patients.length, avgAge, diseaseCount: allDiseases.size, avgBMI }
  }, [patients])

  // 过滤 + 排序
  const filteredPatients = useMemo(() => {
    let list = patients.filter((p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    list = [...list].sort((a, b) => {
      let va: string | number = ''
      let vb: string | number = ''
      if (sortKey === 'name') { va = a.name; vb = b.name }
      else if (sortKey === 'age') { va = a.age; vb = b.age }
      else { va = a.createdAt; vb = b.createdAt }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return list
  }, [patients, searchTerm, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('asc') }
  }

  const resetForm = () => {
    setFormData({ name: '', age: '', gender: '男', height: '', weight: '', allergies: '', chronicDiseases: '', currentMedications: '', medicalHistory: '' })
    setShowAddForm(false)
    setEditingId(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const base = {
      name: formData.name,
      age: parseInt(formData.age),
      gender: formData.gender,
      height: parseFloat(formData.height) || 0,
      weight: parseFloat(formData.weight) || 0,
      allergies: formData.allergies.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      chronicDiseases: formData.chronicDiseases.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      currentMedications: formData.currentMedications.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
      medicalHistory: formData.medicalHistory,
    }
    if (editingId) {
      updatePatient(editingId, base)
    } else {
      addPatient(base)
    }
    resetForm()
  }

  const handleEdit = (patient: Patient) => {
    setFormData({
      name: patient.name,
      age: patient.age.toString(),
      gender: patient.gender,
      height: patient.height.toString(),
      weight: patient.weight.toString(),
      allergies: patient.allergies.join(', '),
      chronicDiseases: patient.chronicDiseases.join(', '),
      currentMedications: patient.currentMedications.join(', '),
      medicalHistory: patient.medicalHistory,
    })
    setEditingId(patient.id)
    setShowAddForm(true)
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

  const SortButton = ({ label, k }: { label: string; k: SortKey }) => (
    <button
      onClick={() => toggleSort(k)}
      className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
        sortKey === k
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      {label}
      <ArrowUpDown className="h-3.5 w-3.5" />
      {sortKey === k && (
        <span className="text-xs">{sortDir === 'asc' ? '↑' : '↓'}</span>
      )}
    </button>
  )

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-2">
            患者档案管理
          </h1>
          <p className="text-muted-foreground">
            管理患者健康信息，为个性化用药推荐提供数据支持
          </p>
        </div>
        <Button onClick={() => { resetForm(); setShowAddForm(true) }} className="gap-2 shadow-lg hover:shadow-xl">
          <Plus className="h-4 w-4" />
          添加患者
        </Button>
      </div>

      {/* Stats Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: Users, label: '患者总数', value: `${stats.total} 人`, color: 'from-blue-500 to-cyan-500' },
          { icon: Calendar, label: '平均年龄', value: `${stats.avgAge} 岁`, color: 'from-purple-500 to-pink-500' },
          { icon: Heart, label: '涉及疾病种类', value: `${stats.diseaseCount} 种`, color: 'from-red-500 to-orange-500' },
          { icon: Scale, label: '平均 BMI', value: stats.avgBMI.toFixed(1), color: 'from-green-500 to-emerald-500' },
        ].map((s) => {
          const Icon = s.icon
          return (
            <Card key={s.label} className="border-border/40 bg-card/50 backdrop-blur hover:shadow-lg transition-all duration-300">
              <CardContent className="pt-5 pb-4">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center mb-3 shadow-md`}>
                  <Icon className="h-5 w-5 text-white" />
                </div>
                <div className="text-2xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  {s.value}
                </div>
                <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Search + Sort */}
      <Card className="border-border/40 bg-card/50 backdrop-blur">
        <CardContent className="pt-6 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="搜索患者姓名..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 h-12"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">排序：</span>
            <SortButton label="姓名" k="name" />
            <SortButton label="年龄" k="age" />
            <SortButton label="建档日期" k="createdAt" />
          </div>
        </CardContent>
      </Card>

      {/* Add/Edit Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
              <CardHeader>
                <div className="flex justify-between items-center">
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
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="p-name">姓名 *</Label>
                      <Input id="p-name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required placeholder="请输入姓名" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="p-age">年龄 *</Label>
                      <Input id="p-age" type="number" value={formData.age} onChange={(e) => setFormData({ ...formData, age: e.target.value })} required placeholder="请输入年龄" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="p-gender">性别 *</Label>
                      <select
                        id="p-gender"
                        value={formData.gender}
                        onChange={(e) => setFormData({ ...formData, gender: e.target.value as PatientGender })}
                        className="flex h-11 w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <option value="男">男</option>
                        <option value="女">女</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="p-height">身高 (cm)</Label>
                        <Input id="p-height" type="number" value={formData.height} onChange={(e) => setFormData({ ...formData, height: e.target.value })} placeholder="175" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="p-weight">体重 (kg)</Label>
                        <Input id="p-weight" type="number" value={formData.weight} onChange={(e) => setFormData({ ...formData, weight: e.target.value })} placeholder="70" />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="p-allergies">过敏史（逗号分隔）</Label>
                    <Input id="p-allergies" value={formData.allergies} onChange={(e) => setFormData({ ...formData, allergies: e.target.value })} placeholder="例如：青霉素，阿司匹林" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="p-diseases">慢性疾病（逗号分隔）</Label>
                    <Input id="p-diseases" value={formData.chronicDiseases} onChange={(e) => setFormData({ ...formData, chronicDiseases: e.target.value })} placeholder="例如：高血压，糖尿病" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="p-meds">当前用药（逗号分隔）</Label>
                    <Input id="p-meds" value={formData.currentMedications} onChange={(e) => setFormData({ ...formData, currentMedications: e.target.value })} placeholder="例如：二甲双胍，氨氯地平" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="p-history">既往病史</Label>
                    <textarea
                      id="p-history"
                      value={formData.medicalHistory}
                      onChange={(e) => setFormData({ ...formData, medicalHistory: e.target.value })}
                      className="flex min-h-[100px] w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                      placeholder="请描述患者既往病史、手术史等"
                    />
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button type="submit" className="gap-2">
                      <Save className="h-4 w-4" />
                      {editingId ? '保存修改' : '添加患者'}
                    </Button>
                    <Button type="button" variant="outline" onClick={resetForm}>取消</Button>
                  </div>
                </CardContent>
              </form>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Patient List */}
      <div className="space-y-3">
        <div className="text-sm text-muted-foreground px-1">
          共 {filteredPatients.length} 条记录{searchTerm && `（搜索"${searchTerm}"）`}
        </div>
        <AnimatePresence>
          {filteredPatients.map((patient, index) => {
            const bmi = calcBMI(patient.weight, patient.height)
            const { label: bmiText, color: bmiColor } = bmiLabel(bmi)
            return (
              <motion.div
                key={patient.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.04 }}
              >
                <Card className="border-border/40 bg-card/50 backdrop-blur hover:shadow-lg transition-all duration-300 overflow-hidden">
                  <CardContent className="p-0">
                    <div className="p-6 cursor-pointer" onClick={() => setExpandedPatient(expandedPatient === patient.id ? null : patient.id)}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4 flex-1 min-w-0">
                          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md flex-shrink-0">
                            <User className="h-7 w-7 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3 mb-2 flex-wrap">
                              <h3 className="text-xl font-semibold">{patient.name}</h3>
                              <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
                                {patient.gender} · {patient.age} 岁
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mb-3">
                              <div className="flex items-center gap-1">
                                <Activity className="h-4 w-4" />
                                <span>BMI: </span>
                                <span className={`font-medium ${bmiColor}`}>{bmi.toFixed(1)} ({bmiText})</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                                <span>{patient.allergies.length} 种过敏</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Calendar className="h-4 w-4" />
                                <span>建档：{patient.createdAt}</span>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {patient.chronicDiseases.slice(0, 3).map((disease) => (
                                <span key={disease} className="px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-medium">
                                  {disease}
                                </span>
                              ))}
                              {patient.chronicDiseases.length > 3 && (
                                <span className="px-3 py-1 rounded-full bg-muted text-muted-foreground text-xs">
                                  +{patient.chronicDiseases.length - 3}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0 ml-3">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="gap-1.5 text-xs text-secondary hover:bg-secondary/10 hover:text-secondary"
                            onClick={(e) => { e.stopPropagation(); handleGoToRecommendation(patient) }}
                          >
                            <Stethoscope className="h-4 w-4" />
                            快速推荐
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => { e.stopPropagation(); handleEdit(patient) }}
                            className="hover:bg-primary/10 hover:text-primary"
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => { e.stopPropagation(); deletePatient(patient.id) }}
                            className="hover:bg-destructive/10 hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon">
                            {expandedPatient === patient.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Expanded Details */}
                    <AnimatePresence>
                      {expandedPatient === patient.id && (
                        <motion.div
                          key="detail"
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="border-t border-border overflow-hidden"
                        >
                          <div className="px-6 pb-6">
                            <div className="grid md:grid-cols-3 gap-6 mt-6">
                              <div>
                                <h4 className="font-semibold mb-3 text-primary text-sm">当前用药</h4>
                                <div className="space-y-2">
                                  {patient.currentMedications.length > 0 ? patient.currentMedications.map((med) => (
                                    <div key={med} className="flex items-center gap-2 p-2.5 rounded-lg bg-primary/5">
                                      <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                                      <span className="text-sm">{med}</span>
                                    </div>
                                  )) : <p className="text-sm text-muted-foreground">无</p>}
                                </div>
                              </div>
                              <div>
                                <h4 className="font-semibold mb-3 text-secondary text-sm">过敏史</h4>
                                <div className="space-y-2">
                                  {patient.allergies.length > 0 ? patient.allergies.map((a) => (
                                    <div key={a} className="flex items-center gap-2 p-2.5 rounded-lg bg-red-50 dark:bg-red-950/30">
                                      <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
                                      <span className="text-sm text-red-600 dark:text-red-400">{a}</span>
                                    </div>
                                  )) : <p className="text-sm text-muted-foreground">无过敏史</p>}
                                </div>
                              </div>
                              <div>
                                <h4 className="font-semibold mb-3 text-sm">体格信息</h4>
                                <div className="space-y-2 text-sm">
                                  <div className="flex justify-between p-2 rounded-lg bg-muted/40">
                                    <span className="text-muted-foreground">身高</span>
                                    <span className="font-medium">{patient.height} cm</span>
                                  </div>
                                  <div className="flex justify-between p-2 rounded-lg bg-muted/40">
                                    <span className="text-muted-foreground">体重</span>
                                    <span className="font-medium">{patient.weight} kg</span>
                                  </div>
                                  <div className="flex justify-between p-2 rounded-lg bg-muted/40">
                                    <span className="text-muted-foreground">BMI</span>
                                    <span className={`font-semibold ${bmiColor}`}>{bmi.toFixed(1)} ({bmiText})</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                            {patient.medicalHistory && (
                              <div className="mt-5 pt-5 border-t border-border">
                                <h4 className="font-semibold mb-2 text-sm">既往病史</h4>
                                <p className="text-sm text-muted-foreground leading-relaxed">{patient.medicalHistory}</p>
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

        {filteredPatients.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="py-12 text-center">
              <User className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-semibold mb-2">未找到患者</h3>
              <p className="text-muted-foreground">
                {searchTerm ? '尝试其他搜索条件' : '点击上方按钮添加第一位患者'}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
