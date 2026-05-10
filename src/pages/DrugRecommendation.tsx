import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import {
  Stethoscope,
  Brain,
  AlertTriangle,

  Info,
  Sparkles,
  Pill,
  FileText,
  Shield,
  TrendingUp,
  Clock,
  Target,
  Lock,
  Key,
  Activity,
  GitCompare,
  Users,
  Printer,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePrivacyStore } from '@/lib/privacyStore'
import { api, getErrorMessage } from '@/lib/api'
import { gaussianSigma, laplaceScale } from '@/lib/privacy'
import { usePatientStore, PatientGender } from '@/lib/patientStore'
import { TextExpander } from '@/components/ui/text-expander'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface RecommendationExplanationFeature {
  name: string
  weight: number
  contribution: number
  note?: string
}

interface RecommendationExplanation {
  features: RecommendationExplanationFeature[]
  warnings: string[]
  evidenceLevel?: string
}

interface RecommendationResultItem {
  drugId: number
  drugName: string
  englishName?: string
  dosage: string
  frequency: string
  confidence: number | null
  score: number
  rawScore: number
  dpNoise?: number | null
  reason: string
  interactions: string[]
  sideEffects: string[]
  category: string
  explanation: RecommendationExplanation
  mode: 'model' | 'demo'
  dpAnomaly?: boolean
  warnings?: string[]
  requiresReview?: boolean
  safetyType?: string
  qualityWarning?: string
  dpConfidence?: { low: number; high: number; ciHalfWidth: number } | null
  matchedDisease?: string
  routingPath?: string
}

interface ExcludedDrug {
  drugName: string
  englishName?: string
  reason: string
  category: string
}

interface PrivacyBudgetInfo {
  epsilonSpent: number
  epsilonBudget: number
  deltaSpent: number
  deltaBudget: number
  warningLevel: string
  remainingRatio: number
  queryCount: number
}

interface GenerateResponse {
  recommendationId: number
  selected: RecommendationResultItem[]
  base: RecommendationResultItem[]
  dp: RecommendationResultItem[]
  dpEnabled: boolean
  excludedDrugs: ExcludedDrug[]
  privacyBudget: PrivacyBudgetInfo | null
  totalCandidates: number
  totalExcluded: number
  totalSafe: number
  dataGaps?: string[]  // v2: 数据缺失提示（由后端返回）
}

interface DrugResult {
  id: string
  drugName: string
  englishName?: string
  dosage: string
  frequency: string
  confidence: number | null
  reason: string
  interactions: string[]
  sideEffects: string[]
  category: string
  explanation: RecommendationExplanation
  mode: 'model' | 'demo'
  score: number
  rawScore: number
  dpNoise?: number | null
  dpAnomaly?: boolean
  warnings?: string[]
  requiresReview?: boolean
  safetyType?: string
  qualityWarning?: string
  dpConfidence?: { low: number; high: number; ciHalfWidth: number } | null
  matchedDisease?: string
  routingPath?: string
  reviewStatus?: 'pending' | 'confirmed' | 'modified' | 'rejected'
}

type InputMode = 'db' | 'manual'

interface PatientData {
  name: string
  age: string
  gender: string
  height: string
  weight: string
  phone: string
  diseases: string
  symptoms: string
  allergies: string
  currentMedications: string
}


const safetyConfig: Record<string, { label: string; color: string; bg: string }> = {
  safe:                    { label: '安全',      color: '#22c55e', bg: '#052e16' },
  relative_contraindication: { label: '需谨慎',  color: '#f59e0b', bg: '#451a03' },
  off_label:               { label: '超说明书',  color: '#f97316', bg: '#431407' },
  unverified:               { label: '待验证',   color: '#a855f7', bg: '#2e1065' },
  data_unverified:          { label: '待验证',   color: '#a855f7', bg: '#2e1065' },
};

function SafetyBadge({ level }: { level: string }) {
  const cfg = safetyConfig[level] || { label: level || '未知', color: '#888', bg: '#111' };
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '1px 6px',
      borderRadius: '3px',
      fontSize: '11px',
      fontWeight: 600,
      color: cfg.color,
      backgroundColor: cfg.bg,
      marginLeft: '6px',
      lineHeight: '18px',
    }}>
      {cfg.label}
    </span>
  );
}

export default function DrugRecommendation() {
  const { config, budget, refresh } = usePrivacyStore()
  const { patients, addPatient } = usePatientStore()
  const location = useLocation()

  const [inputMode, setInputMode] = useState<InputMode>('manual')

  const [patientData, setPatientData] = useState<PatientData>({
    name: '',
    age: '',
    gender: '男',
    height: '',
    weight: '',
    phone: '',
    diseases: '',
    symptoms: '',
    allergies: '',
    currentMedications: '',
  })

  useEffect(() => {
    const state = location.state as { prefill?: Partial<PatientData> } | null
    if (!state?.prefill) return
    setPatientData((prev) => ({ ...prev, ...state.prefill }))
    window.history.replaceState({}, '')
  }, [location.state])

  const [selectedPatientId, setSelectedPatientId] = useState<string>('')
  const [dpEnabled, setDpEnabled] = useState(true)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [recommendations, setRecommendations] = useState<DrugResult[]>([])
  const [comparison, setComparison] = useState<{
    base: RecommendationResultItem[]
    dp: RecommendationResultItem[]
  } | null>(null)
  const [showResults, setShowResults] = useState(false)
  const [selectedDrug, setSelectedDrug] = useState<DrugResult | null>(null)
  const [showExplainability, setShowExplainability] = useState(false)
  const [showConsentDialog, setShowConsentDialog] = useState(false)
  const [consentGiven, setConsentGiven] = useState(() => {
    // 从sessionStorage恢复consent状态
    try {
      return sessionStorage.getItem('dp_consent_given') === 'true'
    } catch { return false }
  })
  const [excludedDrugs, setExcludedDrugs] = useState<ExcludedDrug[]>([])
  const [budgetInfo, setBudgetInfo] = useState<PrivacyBudgetInfo | null>(null)
  const [totalCandidateInfo, setTotalCandidateInfo] = useState<{ total: number; excluded: number; safe: number } | null>(null)
  const [dataGaps, setDataGaps] = useState<string[]>([])
  const [privacyPanelCollapsed, setPrivacyPanelCollapsed] = useState(false)

  const handleSelectPatient = (id: string) => {
    setSelectedPatientId(id)
    if (!id) {
      setInputMode('manual')
      setPatientData({
        name: '', age: '', gender: '男', height: '', weight: '',
        phone: '', diseases: '', symptoms: '', allergies: '', currentMedications: '',
      })
      return
    }

    const patient = patients.find((item) => item.id === id)
    if (!patient) return

    setInputMode('db')
    setPatientData({
      name: patient.name,
      age: String(patient.age),
      gender: patient.gender,
      height: patient.height ? String(patient.height) : '',
      weight: patient.weight ? String(patient.weight) : '',
      phone: patient.phone ?? '',
      diseases: patient.chronicDiseases.join('，'),
      symptoms: patient.medicalHistory,
      allergies: patient.allergies.join('，'),
      currentMedications: patient.currentMedications.join('，'),
    })
  }

  function splitList(value: string) {
    return value.split(/[,，、]/).map((s) => s.trim()).filter(Boolean)
  }

  const autoSaveNewPatient = async () => {
    const trimmedName = patientData.name.trim()
    if (!trimmedName) return

    // 同名患者已存在→切换到DB模式（不创建重复）
    const existing = patients.find((p) => p.name.trim() === trimmedName)
    if (existing) {
      setSelectedPatientId(existing.id)
      setInputMode('db')
      return
    }

    try {
      const newPatient = await addPatient({
        name: trimmedName,
        age: Number(patientData.age) || 0,
        gender: (patientData.gender || '男') as PatientGender,
        height: Number(patientData.height) || 0,
        weight: Number(patientData.weight) || 0,
        phone: patientData.phone?.trim() ?? '',
        allergies: splitList(patientData.allergies),
        chronicDiseases: splitList(patientData.diseases),
        currentMedications: splitList(patientData.currentMedications),
        medicalHistory: patientData.symptoms?.trim() ?? '',
      })
      // 下次推荐自动使用DB模式（含临床指标补充）
      setSelectedPatientId(newPatient.id)
      setInputMode('db')
    } catch (e) {
      // 自动保存失败不影响推荐结果
    }
  }

  const handleAnalyze = async () => {
    // 知情同意检查: 首次使用需确认
    if (!consentGiven) {
      setShowConsentDialog(true)
      return
    }

    setAnalyzeError(null)
    setIsAnalyzing(true)

    try {
      const response = await api.post<GenerateResponse>('/api/recommendations/generate', {
        patientId: inputMode === 'db' && selectedPatientId ? Number(selectedPatientId) : undefined,
        age: patientData.age || undefined,
        gender: patientData.gender || undefined,
        diseases: patientData.diseases || undefined,
        symptoms: patientData.symptoms || undefined,
        allergies: patientData.allergies || undefined,
        currentMedications: patientData.currentMedications || undefined,
        height: patientData.height ? Number(patientData.height) : undefined,
        weight: patientData.weight ? Number(patientData.weight) : undefined,
        dpEnabled,
        dpConfig: dpEnabled ? {
          enabled: true,
          epsilon: config.epsilon,
          delta: config.delta,
          sensitivity: config.sensitivity,
          noiseMechanism: config.noiseMechanism,
          applicationStage: config.applicationStage,
        } : undefined,
        topK: 4,
      })

      setComparison({ base: response.base, dp: response.dp })
      setExcludedDrugs(response.excludedDrugs ?? [])
      setDataGaps(response.dataGaps ?? [])
      setBudgetInfo(response.privacyBudget ?? null)
      setTotalCandidateInfo({
        total: response.totalCandidates,
        excluded: response.totalExcluded,
        safe: response.totalSafe,
      })
      setRecommendations(
        response.selected.map((item) => ({
          id: String(item.drugId),
          drugName: item.drugName,
          dosage: item.dosage,
          frequency: item.frequency,
          confidence: item.confidence,
          reason: item.reason,
          interactions: item.interactions,
          sideEffects: item.sideEffects,
          category: item.category,
          explanation: item.explanation,
          mode: item.mode,
          score: item.score,
          rawScore: item.rawScore,
          dpNoise: item.dpNoise,
          dpAnomaly: item.dpAnomaly,
          warnings: item.warnings,
          requiresReview: item.requiresReview,
          safetyType: item.safetyType,
          englishName: item.englishName,
          qualityWarning: item.qualityWarning,
          dpConfidence: item.dpConfidence,
          matchedDisease: item.matchedDisease,
          routingPath: (item as RecommendationResultItem).routingPath,
          reviewStatus: 'pending' as const,
        }))
      )
      setShowResults(true)
      setSelectedDrug(null)
      setShowExplainability(false)
      await refresh()

      // 手动模式推荐成功后自动保存新患者到档案
      if (inputMode === 'manual' && patientData.name.trim()) {
        await autoSaveNewPatient()
      }
    } catch (error) {
      setAnalyzeError(getErrorMessage(error, '智能分析失败，请稍后重试'))
      setShowResults(false)
      setSelectedDrug(null)
      setRecommendations([])
      setComparison(null)
      setExcludedDrugs([])
      setBudgetInfo(null)
      setTotalCandidateInfo(null)
      setDataGaps([])
    } finally {
      setIsAnalyzing(false)
    }
  }

  const getConfidenceColor = (confidence: number | null) => {
    if (confidence == null) return 'text-muted-foreground'
    if (confidence >= 90) return 'text-ia-data-3'
    if (confidence >= 80) return 'text-brand-sky'
    return 'text-ia-data-4'
  }

  const noiseScale = useMemo(() => {
    if (config.noiseMechanism === 'gaussian') return gaussianSigma(config)
    return laplaceScale(config)
  }, [config])

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="space-y-8">

      {/* 知情同意弹窗 */}
      {showConsentDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-surface-elevated rounded-sm p-6 max-w-md shadow-lg border border-border">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              <h2 className="text-ia-card-title font-heading font-bold text-foreground">知情同意</h2>
            </div>
            <div className="space-y-3 text-ia-body text-muted-foreground">
              <p>在使用本系统前，请确认您已了解以下事项：</p>
              <ul className="list-disc list-inside space-y-1">
                <li>推荐结果由AI模型生成，<strong className="text-foreground">仅供参考，不构成医疗诊断或处方建议</strong></li>
                <li>差分隐私噪声仅保护推荐排序隐私，<strong className="text-foreground">不影响安全排除结果</strong></li>
                <li>计算在本地服务器环境中进行，未使用加密通道</li>
                <li>最终用药决策须由执业医师确认</li>
              </ul>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => {
                  setConsentGiven(true)
                  // 持久化consent到sessionStorage (页面刷新不丢失)
                  try { sessionStorage.setItem('dp_consent_given', 'true') } catch {}
                  // 调用consent审计API记录
                  api.post('/model/audit/consent', {
                    action: 'consent_given',
                    timestamp: new Date().toISOString(),
                  }).catch(() => {})
                  setShowConsentDialog(false)
                }}
                className="px-4 py-2 rounded-sm bg-gradient-to-br from-brand-sky to-sky-600 text-white font-heading font-semibold text-ia-label hover:bg-brand-sky/90"
              >
                我已了解，继续使用
              </button>
              <button
                onClick={() => setShowConsentDialog(false)}
                className="px-4 py-2 rounded-sm bg-surface text-muted-foreground font-heading font-semibold text-ia-label hover:bg-surface/80"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Page Header — Border-left editorial */}
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-start gap-4">
          <div className="hidden md:flex h-10 w-10 items-center justify-center rounded-sm bg-gradient-to-br from-brand-sky to-sky-600 flex-shrink-0">
            <Stethoscope className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-ia-tile font-display font-bold text-foreground mb-2">
              智能用药推荐
            </h1>
            <p className="text-ia-body text-muted-foreground max-w-2xl">
              基于深度学习模型的个性化用药建议，融合差分隐私保护技术
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              {['DeepFM', '注意力机制', '图神经网络', 'DP-SGD'].map((tag) => (
                <span key={tag} className="ia-badge ia-badge-primary">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Main content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Form area */}
        <div className="lg:col-span-2 space-y-6">
          <Card hover="none">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-gradient-to-br from-brand-sky to-sky-600">
                  <FileText className="h-4 w-4 text-white" />
                </div>
                <div>
                  <CardTitle>患者信息录入</CardTitle>
                  <CardDescription>填写患者临床信息以获取个性化推荐</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Mode toggle */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (inputMode !== 'db') {
                      setInputMode('db')
                      if (selectedPatientId) handleSelectPatient(selectedPatientId)
                    }
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-ia-caption font-heading font-semibold transition-colors duration-150 cursor-pointer ${
                    inputMode === 'db'
                      ? 'bg-gradient-to-br from-brand-sky to-sky-600 text-white border-brand-sky'
                      : 'bg-surface-elevated text-foreground border-white/[0.06] hover:bg-surface'
                  }`}
                >
                  <Users className="h-3.5 w-3.5" />
                  从档案选择
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setInputMode('manual')
                    setSelectedPatientId('')
                    setPatientData({
                      name: '', age: '', gender: '男', height: '', weight: '',
                      phone: '', diseases: '', symptoms: '', allergies: '', currentMedications: '',
                    })
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-ia-caption font-heading font-semibold transition-colors duration-150 cursor-pointer ${
                    inputMode === 'manual'
                      ? 'bg-gradient-to-br from-brand-sky to-sky-600 text-white border-brand-sky'
                      : 'bg-surface-elevated text-foreground border-white/[0.06] hover:bg-surface'
                  }`}
                >
                  <FileText className="h-3.5 w-3.5" />
                  手动填写
                </button>
              </div>

              {/* Patient dropdown (always visible) */}
              <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                <Label htmlFor="quick-select" className="flex items-center gap-2 mb-2 text-ia-caption font-heading font-semibold">
                  <Users className="h-3.5 w-3.5 text-brand-sky" />
                  患者档案
                </Label>
                <select
                  id="quick-select"
                  value={selectedPatientId}
                  onChange={(e) => handleSelectPatient(e.target.value)}
                  className="flex h-10 w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-brand-sky focus-visible:ring-1 focus-visible:ring-brand-sky"
                >
                  <option value="">-- 选择已有患者（可选）--</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} · {p.gender} · {p.age}岁 · {p.chronicDiseases.slice(0, 2).join('、')}
                    </option>
                  ))}
                </select>
              </div>

              {/* Mode info banner */}
              {inputMode === 'db' && selectedPatientId && (
                <div className="p-2.5 rounded-sm bg-brand-sky/5 border border-brand-sky/10 text-ia-caption text-brand-sky flex items-center gap-2">
                  <Info className="h-3.5 w-3.5" />
                  已从患者档案自动填充。临床指标（肾功能、肝功能、妊娠状态等）将由系统从健康档案自动补充。
                </div>
              )}
              {inputMode === 'manual' && (
                <div className="p-2.5 rounded-sm bg-secondary/5 border border-secondary/10 text-ia-caption text-secondary flex items-center gap-2">
                  <Info className="h-3.5 w-3.5" />
                  推荐完成后，患者信息将自动保存到档案。下次推荐即可使用完整的临床指标数据。
                </div>
              )}

              {/* Patient info form */}
              <div className="space-y-1.5">
                <Label htmlFor="name" className="text-ia-caption font-heading font-semibold">
                  姓名 {inputMode === 'manual' && <span className="text-destructive">*</span>}
                </Label>
                <Input
                  id="name"
                  value={patientData.name}
                  onChange={(e) => setPatientData({ ...patientData, name: e.target.value })}
                  placeholder={inputMode === 'db' ? '（自动填充）' : '患者姓名'}
                  className={`placeholder:text-muted-foreground/40 placeholder:text-sm ${inputMode === 'db' && patientData.name ? 'bg-surface/50' : ''}`}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="age" className="text-ia-caption font-heading font-semibold">年龄 *</Label>
                  <Input id="age" type="number" value={patientData.age} onChange={(e) => setPatientData({ ...patientData, age: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="65" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="gender" className="text-ia-caption font-heading font-semibold">性别 *</Label>
                  <select
                    id="gender"
                    value={patientData.gender}
                    onChange={(e) => setPatientData({ ...patientData, gender: e.target.value })}
                    className="flex h-10 w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-brand-sky focus-visible:ring-1 focus-visible:ring-brand-sky"
                  >
                    <option value="男">男</option>
                    <option value="女">女</option>
                    <option value="未知">未知</option>
                  </select>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="height" className="text-ia-caption font-heading font-semibold">
                    身高 (cm)
                    {inputMode === 'manual' && <span className="text-ia-label text-muted-foreground ml-1">推荐补充，用于BMI计算</span>}
                  </Label>
                  <Input id="height" type="number" value={patientData.height} onChange={(e) => setPatientData({ ...patientData, height: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="170" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="weight" className="text-ia-caption font-heading font-semibold">
                    体重 (kg)
                    {inputMode === 'manual' && <span className="text-ia-label text-muted-foreground ml-1">推荐补充，用于BMI计算</span>}
                  </Label>
                  <Input id="weight" type="number" value={patientData.weight} onChange={(e) => setPatientData({ ...patientData, weight: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="65" />
                </div>
              </div>

              {inputMode === 'manual' && (
                <div className="space-y-1.5">
                  <Label htmlFor="phone" className="text-ia-caption font-heading font-semibold">
                    联系电话 <span className="text-ia-label text-muted-foreground">（可选）</span>
                  </Label>
                  <Input id="phone" value={patientData.phone} onChange={(e) => setPatientData({ ...patientData, phone: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="13800138000" />
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="diseases" className="text-ia-caption font-heading font-semibold">确诊疾病（逗号分隔）*</Label>
                <Input id="diseases" value={patientData.diseases} onChange={(e) => setPatientData({ ...patientData, diseases: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="高血压，2型糖尿病" />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="symptoms" className="text-ia-caption font-heading font-semibold">主要症状</Label>
                <textarea
                  id="symptoms"
                  value={patientData.symptoms}
                  onChange={(e) => setPatientData({ ...patientData, symptoms: e.target.value })}
                  className="flex min-h-[80px] w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-2 text-ia-body font-body placeholder:text-muted-foreground/40 placeholder:text-sm focus-visible:outline-none focus-visible:border-brand-sky focus-visible:ring-1 focus-visible:ring-brand-sky resize-none"
                  placeholder="头晕、胸闷、多尿、口渴"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="allergies" className="text-ia-caption font-heading font-semibold">过敏史</Label>
                  <Input id="allergies" value={patientData.allergies} onChange={(e) => setPatientData({ ...patientData, allergies: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="青霉素，磺胺类" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="currentMedications" className="text-ia-caption font-heading font-semibold">当前用药</Label>
                  <Input id="currentMedications" value={patientData.currentMedications} onChange={(e) => setPatientData({ ...patientData, currentMedications: e.target.value })} className="placeholder:text-muted-foreground/40 placeholder:text-sm" placeholder="二甲双胍，阿司匹林" />
                </div>
              </div>

              {/* Privacy Level Control */}
              <div className="pt-4 border-t border-white/[0.06]">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <Label className="text-ia-caption font-heading font-semibold flex items-center gap-2">
                      <Shield className="h-3.5 w-3.5 text-brand-sky" />
                      差分隐私推理开关
                    </Label>
                    <p className="text-ia-label text-muted-foreground mt-1">
                      关闭后展示「无 DP」基线结果；开启后对药物评分注入噪声，并记录隐私预算消耗。
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDpEnabled((v) => !v)}
                    className={`px-3 py-1.5 rounded-sm border text-ia-caption font-heading font-semibold transition-colors duration-150 cursor-pointer ${
                      dpEnabled
                        ? 'bg-gradient-to-br from-brand-sky to-sky-600 text-white border-brand-sky'
                        : 'bg-surface-elevated text-foreground border-white/[0.06] hover:bg-surface'
                    }`}
                  >
                    {dpEnabled ? '已开启' : '已关闭'}
                  </button>
                </div>

                <div className="grid md:grid-cols-3 gap-2">
                  <div className="p-2.5 rounded-sm bg-surface border border-white/[0.06]">
                    <div className="text-ia-label text-muted-foreground">当前 ε</div>
                    <div className="text-ia-body font-heading font-bold text-brand-sky">{config.epsilon.toFixed(3)}</div>
                  </div>
                  <div className="p-2.5 rounded-sm bg-surface border border-white/[0.06]">
                    <div className="text-ia-label text-muted-foreground">噪声规模</div>
                    <div className="text-ia-body font-heading font-bold">
                      {config.noiseMechanism === 'gaussian' ? 'σ' : 'b'} = {noiseScale.toFixed(3)}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-sm bg-surface border border-white/[0.06]">
                    <div className="text-ia-label text-muted-foreground">预算剩余</div>
                    <div className="text-ia-body font-heading font-bold text-secondary">ε_rem = {budget.remaining.toFixed(2)}</div>
                  </div>
                </div>
              </div>

              {analyzeError && (
                <div className="rounded-sm border border-destructive/30 bg-destructive/6 p-2.5 text-ia-caption text-destructive">
                  {analyzeError}
                </div>
              )}

              <Button
                onClick={handleAnalyze}
                className="w-full gap-2"
                size="lg"
                loading={isAnalyzing}
                disabled={isAnalyzing || !patientData.diseases || (inputMode === 'manual' && !patientData.name.trim())}
              >
                <Sparkles className="h-4 w-4" />
                开始智能推荐
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right: Privacy panel (collapsible) */}
        <div className="space-y-6">
          <Card hover="none" className="sticky top-20">
            <div className="h-0.5 bg-gradient-to-br from-brand-sky to-sky-600" />
            <CardHeader className="cursor-pointer" onClick={() => setPrivacyPanelCollapsed(!privacyPanelCollapsed)}>
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield className="h-4 w-4 text-brand-sky" />
                隐私保护状态
                {privacyPanelCollapsed ? <ChevronDown className="h-3.5 w-3.5 ml-auto" /> : <ChevronUp className="h-3.5 w-3.5 ml-auto" />}
              </CardTitle>
              {!privacyPanelCollapsed && <CardDescription>当前会话的隐私指标</CardDescription>}
            </CardHeader>
            {!privacyPanelCollapsed && <CardContent className="space-y-3">
              <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                <div className="flex items-center gap-2 mb-1.5">
                  <Lock className="h-3.5 w-3.5 text-brand-sky" />
                  <span className="text-ia-caption font-heading font-semibold">差分隐私机制</span>
                </div>
                <div className="text-ia-body font-heading font-bold">
                  {dpEnabled ? `${config.noiseMechanism} 扰动` : '未启用 DP（基线）'}
                </div>
                <p className="text-ia-label text-muted-foreground">
                  注入阶段：{config.applicationStage === 'data' ? '数据层' : config.applicationStage === 'gradient' ? '梯度层' : '模型层'}
                </p>
              </div>

              <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                <div className="flex items-center gap-2 mb-1.5">
                  <Key className="h-3.5 w-3.5 text-secondary" />
                  <span className="text-ia-caption font-heading font-semibold">隐私预算消耗</span>
                </div>
                <div className="text-ia-body font-heading font-bold">ε_total = {config.privacyBudget.toFixed(1)}</div>
                <div className="progress-bar mt-2">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }}
                  />
                </div>
                <p className="text-ia-label text-muted-foreground mt-1.5">
                  已消耗 ε = {budget.spent.toFixed(2)} · 剩余 ε = {budget.remaining.toFixed(2)}
                </p>
              </div>

              <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                <div className="flex items-center gap-2 mb-1.5">
                  <Activity className="h-3.5 w-3.5 text-ia-data-4" />
                  <span className="text-ia-caption font-heading font-semibold">噪声规模</span>
                </div>
                <div className="text-ia-body font-heading font-bold">
                  {config.noiseMechanism === 'gaussian' ? 'σ' : 'b'} = {noiseScale.toFixed(3)}
                </div>
                <p className="text-ia-label text-muted-foreground">
                  {config.noiseMechanism === 'gaussian' ? `(ε,δ)-DP · δ=${config.delta.toExponential(2)}` : 'ε-DP（纯 DP）'}
                </p>
              </div>

              <div className="p-3 rounded-sm border border-ia-data-3/30 bg-ia-data-3/6">
                <div className="flex items-center gap-2 text-ia-data-3">
                  <Info className="h-3.5 w-3.5" />
                  <span className="text-ia-caption font-heading font-semibold">隐私保护说明</span>
                </div>
                <p className="text-ia-label text-ia-data-3/80 mt-1">
                  差分隐私噪声机制已应用于推荐评分，降低个体推断风险。DP仅保护排序隐私，不影响安全排除结果。计算在本地服务器环境中进行。
                </p>
              </div>
            </CardContent>}
          </Card>
        </div>
      </div>

      {/* Results Section */}
      <AnimatePresence>
        {showResults && (
          <div className="animate-fade-in print-area">
            <Card hover="none" className="border-brand-sky/20">
              <CardHeader>
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-gradient-to-br from-brand-sky to-sky-600">
                      <Stethoscope className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <CardTitle>推荐结果</CardTitle>
                      <CardDescription>
                        基于深度学习模型分析，为您生成以下个性化用药建议
                      </CardDescription>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="gap-2 no-print cursor-pointer" onClick={handlePrint}>
                    <Printer className="h-3.5 w-3.5" />
                    打印 / 导出
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* DP comparison */}
                {comparison && (
                  <div className="mb-5 p-3 rounded-sm bg-surface border border-white/[0.06]">
                    <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
                      <div className="flex items-center gap-2">
                        <GitCompare className="h-3.5 w-3.5 text-brand-sky" />
                        <span className="text-ia-caption font-heading font-semibold">有/无 DP 结果对比（Top-4）</span>
                      </div>
                      <div className="text-ia-label text-muted-foreground">
                        {dpEnabled ? '当前展示：DP 结果' : '当前展示：基线结果'}
                      </div>
                    </div>
                    <div className="grid md:grid-cols-2 gap-2 text-ia-caption">
                      <div className="p-2.5 rounded-sm bg-surface-elevated border border-white/[0.06]">
                        <div className="text-ia-label text-muted-foreground mb-1.5">无 DP（基线）</div>
                        <ol className="space-y-0.5">
                          {comparison.base.map((r, idx) => (
                            <li key={`${r.drugId}-${idx}`} className="flex justify-between gap-2">
                              <span className="truncate">{idx + 1}. {r.drugName}</span>
                              <span className="text-muted-foreground">score {r.score.toFixed(2)}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                      <div className="p-2.5 rounded-sm border border-brand-sky/20 bg-brand-sky/4">
                        <div className="text-ia-label text-muted-foreground mb-1.5">差分隐私（噪声后）</div>
                        <ol className="space-y-0.5">
                          {comparison.dp.map((r, idx) => (
                            <li key={`${r.drugId}-${idx}`} className="flex justify-between gap-2">
                              <span className="truncate">{idx + 1}. {r.drugName}</span>
                              <span className="text-muted-foreground">
                                score {r.score.toFixed(2)}
                                {typeof r.dpNoise === 'number' ? ` (noise ${r.dpNoise >= 0 ? '+' : ''}${r.dpNoise.toFixed(2)})` : ''}
                              </span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    </div>
                  </div>
                )}

                {/* Data Gaps Warning */}
                {dataGaps.length > 0 && (
                  <div className="mb-5 p-3 rounded-sm bg-amber-50 border border-amber-200">
                    <div className="flex items-center gap-2 text-amber-700">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span className="text-ia-caption font-heading font-semibold">患者数据缺失提示</span>
                    </div>
                    <p className="text-ia-label text-amber-600 mt-1">
                      以下数据缺失，相关安全过滤未启用。建议补充完整信息以获得更精准推荐：
                    </p>
                    <ul className="mt-2 space-y-1">
                      {dataGaps.map((gap) => (
                        <li key={`gap-${gap}`} className="text-ia-caption text-amber-700 flex items-center gap-1.5">
                          <span className="text-amber-500">·</span>
                          {gap}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Empty State */}
                {recommendations.length === 0 && showResults && (
                  <div className="mb-5 p-4 rounded-sm bg-surface border border-white/[0.06] text-center">
                    <div className="flex items-center justify-center gap-2 mb-2 text-muted-foreground">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="font-heading font-semibold">无法给出可信推荐</span>
                    </div>
                    <p className="text-ia-label text-muted-foreground">
                      当前条件下所有候选药物均被安全排除，或模型未返回有效推荐。建议补充患者信息后重新分析。
                    </p>
                  </div>
                )}

                {/* Drug Cards */}
                <div className="grid md:grid-cols-2 gap-3 mb-5">
                  {recommendations.map((rec) => (
                    <div
                      key={rec.id}
                      onClick={() => setSelectedDrug(selectedDrug?.id === rec.id ? null : rec)}
                      className={`rounded-lg border border-white/[0.06] bg-surface-elevated p-4 shadow-xs transition-all duration-200 hover:-translate-y-1 hover:shadow-sm hover:border-brand-sky/15 cursor-pointer ${
                        selectedDrug?.id === rec.id
                          ? 'border-brand-sky ia-border-3'
                          : ''
                      } ${rec.dpAnomaly ? 'border-ia-data-4/50' : ''}`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <Pill className="h-4 w-4 text-brand-sky" />
                            <h4 className="font-heading font-semibold text-ia-card-title">
                              <span style={{ display: 'inline-flex', alignItems: 'center' }}>
                                {rec.drugName}
                                <SafetyBadge level={rec.safetyType || 'safe'} />
                                {rec.explanation?.evidenceLevel && (
                                  <span style={{
                                    display: 'inline-block',
                                    marginLeft: '6px',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    fontSize: '10px',
                                    fontWeight: 600,
                                    background: rec.explanation.evidenceLevel === 'on_label' ? '#052e16' : '#451a03',
                                    color: rec.explanation.evidenceLevel === 'on_label' ? '#22c55e' : '#f59e0b',
                                  }}>
                                    {rec.explanation.evidenceLevel === 'on_label' ? '说明书内' : '超说明书'}
                                  </span>
                                )}
                                {rec.reviewStatus && (
                                  <span style={{
                                    display: 'inline-block',
                                    marginLeft: '6px',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    fontSize: '10px',
                                    fontWeight: 600,
                                    background:
                                      rec.reviewStatus === 'confirmed' ? '#052e16' :
                                      rec.reviewStatus === 'modified' ? '#1e3a5f' :
                                      rec.reviewStatus === 'rejected' ? '#450a0a' : '#1a1a2e',
                                    color:
                                      rec.reviewStatus === 'confirmed' ? '#22c55e' :
                                      rec.reviewStatus === 'modified' ? '#60a5fa' :
                                      rec.reviewStatus === 'rejected' ? '#f87171' : '#888',
                                  }}>
                                    {rec.reviewStatus === 'pending' ? '待审核' :
                                     rec.reviewStatus === 'confirmed' ? '已确认' :
                                     rec.reviewStatus === 'modified' ? '已修改' : '已拒绝'}
                                  </span>
                                )}
                              </span>
                            </h4>
                            {rec.englishName && (
                              <span className="text-xs text-muted-foreground font-mono">{rec.englishName}</span>
                            )}
                            <span className={`ia-badge text-[10px] px-1.5 py-0.5 ${
                              rec.mode === 'model'
                                ? 'bg-brand-sky/10 text-brand-sky border-brand-sky/20'
                                : 'bg-surface text-muted-foreground border-white/[0.06]'
                            }`}>
                              {rec.mode === 'model' ? '模型推理' : '演示模式'}
                            </span>
                            {rec.requiresReview && (
                              <span className="ia-badge text-[10px] px-1.5 py-0.5 bg-ia-data-4/10 text-ia-data-4 border-ia-data-4/20">
                                需审核
                              </span>
                            )}
                            {rec.qualityWarning && (
                              <span className="ia-badge text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 border-amber-200">
                                {rec.qualityWarning}
                              </span>
                            )}
                            {rec.dpAnomaly && (
                              <span className="ia-badge text-[10px] px-1.5 py-0.5 bg-rose-100 text-rose-700 border-rose-200">
                                DP噪声警示
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="ia-badge ia-badge-primary">
                              {rec.category}
                            </span>
                            {rec.matchedDisease && (
                              <span className="ia-badge text-[10px] px-1.5 py-0.5 bg-brand-sky/10 text-brand-sky border-brand-sky/20">
                                匹配疾病: {rec.matchedDisease}
                              </span>
                            )}
                          </div>

                          {/* Routing Path Explanation */}
                          {rec.category && rec.matchedDisease && rec.matchedDisease !== '未知' && (
                            <div style={{
                              fontSize: '11px',
                              color: '#888',
                              marginTop: '6px',
                              padding: '4px 8px',
                              background: '#16213e',
                              borderRadius: '4px',
                              lineHeight: '1.5',
                            }}>
                              <span style={{ color: '#00d4aa' }}>推荐路径：</span>
                              疾病匹配 → <span style={{ color: '#ffd93d' }}>{rec.matchedDisease}</span>
                              {rec.category && <> → <span style={{ color: '#6c5ce7' }}>{rec.category}</span></>}
                            </div>
                          )}
                        </div>
                        <div className="text-right">
                          <div className={`text-xl font-heading font-bold ${getConfidenceColor(rec.confidence)}`}>
                            {rec.confidence != null ? `${rec.confidence}%` : '--'}
                          </div>
                          <div className="text-ia-label text-muted-foreground">置信度</div>
                        </div>
                      </div>

                      <div className="text-ia-caption text-muted-foreground flex items-center gap-2">
                        <Target className="h-3.5 w-3.5" />
                        <span>{rec.dosage} · {rec.frequency}</span>
                      </div>

                      {/* Safety: doctor-review-required indicator */}
                      {rec.safetyType && rec.safetyType !== 'safe' && (
                        <div style={{ color: '#f59e0b', fontSize: '11px', marginTop: '2px' }}>
                          {'⚠ 需医生审核'}
                        </div>
                      )}

                      {/* Score breakdown */}
                      {dpEnabled && rec.rawScore !== undefined && (
                        <div className="mt-2 text-ia-label text-muted-foreground flex items-center gap-1.5">
                          <span>原始评分: {rec.rawScore.toFixed(3)}</span>
                          {typeof rec.dpNoise === 'number' && (
                            <>
                              <span>→</span>
                              <span>DP评分: {rec.score.toFixed(3)}</span>
                              <span className={`text-[10px] ${rec.dpNoise >= 0 ? 'text-brand-sky' : 'text-ia-data-4'}`}>
                                (噪声 {rec.dpNoise >= 0 ? '+' : ''}{rec.dpNoise.toFixed(3)})
                              </span>
                            </>
                          )}
                          {rec.dpConfidence && (
                            <div className="mt-1 flex items-center gap-2">
                              <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                                置信区间
                              </span>
                              <div className="relative h-2 w-24 bg-surface rounded-full overflow-hidden">
                                <div
                                  className="absolute h-full bg-brand-sky/40 rounded-full"
                                  style={{
                                    left: `${Math.max(0, rec.dpConfidence.low) * 100}%`,
                                    width: `${(Math.min(1, rec.dpConfidence.high) - Math.max(0, rec.dpConfidence.low)) * 100}%`,
                                  }}
                                />
                                <div
                                  className="absolute h-full w-1 bg-gradient-to-br from-brand-sky to-sky-600 rounded"
                                  style={{ left: `${rec.score * 100}%` }}
                                />
                              </div>
                              <span className="text-[10px] text-muted-foreground">
                                [{rec.dpConfidence.low.toFixed(2)}–{rec.dpConfidence.high.toFixed(2)}]
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* DP anomaly warning */}
                      {rec.dpAnomaly && (
                        <div className="mt-2 flex items-center gap-1.5 text-ia-caption text-ia-data-4">
                          <AlertTriangle className="h-3 w-3" />
                          <span>DP噪声可能导致排序异常（原始评分极低）</span>
                        </div>
                      )}

                      {/* Safety warnings */}
                      {rec.warnings && rec.warnings.length > 0 && (
                        <div className="mt-2 flex items-center gap-1.5 text-ia-caption text-secondary">
                          <Info className="h-3 w-3" />
                          <span>{rec.warnings.join('；')}</span>
                        </div>
                      )}

                      <div className="mt-3">
                        <div className="progress-bar">
                          <div
                            className="progress-bar-fill"
                            style={{ width: `${rec.confidence ?? 0}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Excluded Drugs & Budget Info */}
                {(excludedDrugs.length > 0 || budgetInfo || totalCandidateInfo) && (
                  <div className="mb-5 grid md:grid-cols-2 gap-3">
                    {/* Excluded drugs section */}
                    {excludedDrugs.length > 0 && (
                      <div className="p-3 rounded-sm bg-destructive/4 border border-destructive/20">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                          <span className="text-ia-caption font-heading font-semibold text-destructive">
                            安全排除药物（{excludedDrugs.length} 项）
                          </span>
                        </div>
                        <p className="text-ia-label text-muted-foreground mb-2">
                          以下药物因安全原因被排除，不受差分隐私噪声影响
                        </p>
                        <div className="max-h-40 overflow-y-auto space-y-1">
                          {excludedDrugs.map((d, i) => (
                            <div key={d.englishName || d.drugName || String(i)} className="flex items-start gap-2 text-ia-caption">
                              <span className="text-destructive mt-0.5">·</span>
                              <div>
                                <span className="font-heading font-semibold">{d.drugName}</span>
                                <span className="text-muted-foreground ml-1.5">({d.category})</span>
                                <span className="text-muted-foreground ml-1">— {d.reason}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Candidate stats & budget info */}
                    {(totalCandidateInfo || budgetInfo) && (
                      <div className="p-3 rounded-sm bg-surface border border-white/[0.06] space-y-3">
                        {totalCandidateInfo && (
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <Shield className="h-3.5 w-3.5 text-brand-sky" />
                              <span className="text-ia-caption font-heading font-semibold">候选药物筛选</span>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-ia-label">
                              <div className="p-2 rounded-sm bg-surface-elevated border border-white/[0.06] text-center">
                                <div className="font-heading font-bold text-foreground">{totalCandidateInfo.total}</div>
                                <div className="text-muted-foreground">总候选</div>
                              </div>
                              <div className="p-2 rounded-sm bg-destructive/6 border border-destructive/20 text-center">
                                <div className="font-heading font-bold text-destructive">{totalCandidateInfo.excluded}</div>
                                <div className="text-muted-foreground">已排除</div>
                              </div>
                              <div className="p-2 rounded-sm bg-brand-sky/6 border border-brand-sky/20 text-center">
                                <div className="font-heading font-bold text-brand-sky">{totalCandidateInfo.safe}</div>
                                <div className="text-muted-foreground">安全候选</div>
                              </div>
                            </div>
                          </div>
                        )}
                        {budgetInfo && (
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <Lock className="h-3.5 w-3.5 text-secondary" />
                              <span className="text-ia-caption font-heading font-semibold">本次查询隐私预算</span>
                            </div>
                            <div className="p-2 rounded-sm bg-surface-elevated border border-white/[0.06] text-ia-label">
                              <div className="flex justify-between mb-1">
                                <span className="text-muted-foreground">ε 已消耗</span>
                                <span className={`font-heading font-bold ${
                                  budgetInfo.warningLevel === 'EXCEEDED' ? 'text-destructive' :
                                  budgetInfo.warningLevel === 'CRITICAL_80' ? 'text-ia-data-4' :
                                  budgetInfo.warningLevel === 'WARNING_50' ? 'text-secondary' : 'text-foreground'
                                }`}>
                                  {budgetInfo.epsilonSpent.toFixed(4)} / {budgetInfo.epsilonBudget.toFixed(1)}
                                </span>
                              </div>
                              <div className="progress-bar mb-1.5">
                                <div
                                  className={`progress-bar-fill ${
                                    budgetInfo.warningLevel === 'EXCEEDED' ? 'bg-destructive' :
                                    budgetInfo.warningLevel === 'CRITICAL_80' ? 'bg-ia-data-4' :
                                    budgetInfo.warningLevel === 'WARNING_50' ? 'bg-secondary' : ''
                                  }`}
                                  style={{ width: `${Math.min(100, (budgetInfo.epsilonSpent / budgetInfo.epsilonBudget) * 100)}%` }}
                                />
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">查询 #{budgetInfo.queryCount}</span>
                                <span className="text-muted-foreground">剩余 {((budgetInfo.remainingRatio) * 100).toFixed(1)}%</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Detailed Drug Information */}
                {selectedDrug && (
                  <div className="border-t border-white/[0.06] pt-5">
                    <div className="p-5 rounded-sm bg-surface border border-white/[0.06] space-y-5">
                      <h4 className="font-heading font-semibold text-ia-card-title flex items-center gap-2">
                        <Info className="h-4 w-4 text-brand-sky" />
                        详细用药说明 — {selectedDrug.drugName}
                      </h4>

                      <div className="grid md:grid-cols-2 gap-5">
                        <div className="space-y-4">
                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <TrendingUp className="h-3.5 w-3.5 text-brand-sky" />
                              推荐理由
                            </h5>
                            <TextExpander text={selectedDrug.reason} maxLines={3} expandText="查看完整理由" collapseText="收起理由" />
                          </div>

                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <Clock className="h-3.5 w-3.5 text-secondary" />
                              用法用量
                            </h5>
                            <div className="p-2.5 rounded-sm bg-surface-elevated border border-white/[0.06]">
                              <p className="text-ia-caption"><strong>剂量：</strong>{selectedDrug.dosage}</p>
                              <p className="text-ia-caption"><strong>频率：</strong>{selectedDrug.frequency}</p>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-4">
                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <AlertTriangle className="h-3.5 w-3.5 text-ia-data-4" />
                              药物相互作用
                            </h5>
                            <div className="space-y-1.5">
                              {selectedDrug.interactions.map((interaction, i) => (
                                <div key={`int-${i}-${interaction.substring(0,20)}`} className="p-2.5 rounded-sm border border-ia-data-4/30 bg-ia-data-4/6">
                                  <p className="text-ia-caption text-ia-data-4">{interaction}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <Info className="h-3.5 w-3.5 text-brand-sky" />
                              常见副作用
                            </h5>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedDrug.sideEffects.map((effect) => (
                                <span key={`se-${effect}`} className="ia-badge ia-badge-primary">
                                  {effect}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Safety Warnings */}
                      {selectedDrug.explanation.warnings.length > 0 && (
                        <div className="p-3 rounded-sm border border-destructive/30 bg-destructive/6">
                          <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2 text-destructive">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            安全警示
                          </h5>
                          <ul className="space-y-1">
                            {selectedDrug.explanation.warnings.map((w, i) => (
                              <li key={`warn-${i}-${w.substring(0,20)}`} className="text-ia-caption text-destructive flex items-start gap-2">
                                <span className="mt-0.5">·</span>
                                <span>{w}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Model Explainability */}
                      <div>
                        <button
                          onClick={() => setShowExplainability(!showExplainability)}
                          className="flex items-center gap-2 text-ia-caption font-heading font-semibold text-brand-sky hover:underline cursor-pointer mb-3"
                        >
                          <Brain className="h-3.5 w-3.5" />
                          模型可解释性分析
                          {showExplainability ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>

                        <AnimatePresence>
                          {showExplainability && (
                            <div className="animate-fade-in overflow-hidden">
                              <div className="p-4 rounded-sm bg-surface-elevated border border-white/[0.06]">
                                <p className="text-ia-label text-muted-foreground mb-3">
                                  以下展示深度学习模型各特征维度对本次推荐评分的贡献（基于 DeepFM 注意力权重分析）
                                </p>
                                <div className="h-[220px]">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <BarChart
                                      data={selectedDrug.explanation.features.map((f) => ({
                                        name: f.name,
                                        contribution: Math.round(f.contribution * 100) / 100,
                                      }))}
                                      layout="vertical"
                                      margin={{ left: 10, right: 20 }}
                                    >
                                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                      <XAxis type="number" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 10 }} />
                                      <YAxis
                                        dataKey="name"
                                        type="category"
                                        width={100}
                                        stroke="hsl(var(--muted-foreground))"
                                        tick={{ fontSize: 10 }}
                                      />
                                      <Tooltip
                                        contentStyle={{
                                          backgroundColor: 'hsl(var(--card))',
                                          border: '1px solid hsl(var(--border))',
                                          borderRadius: '3px',
                                          fontSize: '11px',
                                        }}
                                        formatter={(v: number) => [v.toFixed(3), '贡献值']}
                                      />
                                      <Bar dataKey="contribution" name="特征贡献" radius={[0, 2, 2, 0]}>
                                        {selectedDrug.explanation.features.map((f, i) => (
                                          <Cell
                                            key={i}
                                            fill={f.contribution >= 0 ? 'hsl(var(--primary))' : 'hsl(var(--destructive))'}
                                            fillOpacity={0.85}
                                          />
                                        ))}
                                      </Bar>
                                    </BarChart>
                                  </ResponsiveContainer>
                                </div>
                                <p className="text-ia-label text-muted-foreground mt-2">
                                  正值（蓝色）表示该特征增强推荐，负值（红色）表示该特征降低推荐评分
                                </p>
                              </div>
                            </div>
                          )}
                        </AnimatePresence>
                      </div>

                      {/* Privacy Notice */}
                      <div className="pt-4 border-t border-white/[0.06]">
                        <div className="flex items-start gap-3 p-3 rounded-sm border border-brand-sky/20 bg-brand-sky/4">
                          <Shield className="h-4 w-4 text-brand-sky flex-shrink-0 mt-0.5" />
                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-1 text-brand-sky">
                              隐私保护说明
                            </h5>
                            <div className="text-ia-caption text-muted-foreground space-y-1">
                              <p>
                                推荐模式：<strong className="text-foreground">
                                  {selectedDrug.mode === 'model' ? '模型推理（DeepFM）' : '演示模式（规则匹配）'}
                                </strong>
                              </p>
                              <p>
                                {dpEnabled
                                  ? '差分隐私噪声仅保护推荐排序隐私，不影响安全排除结果。推荐评分已注入随机噪声以降低推断风险。'
                                  : '本次以无 DP 基线方式生成，未注入噪声，仅用于对比展示。'}
                                （ε = {config.epsilon.toFixed(3)}）
                              </p>
                              {selectedDrug.dpAnomaly && (
                                <p className="text-ia-data-4">
                                  注意：该药物原始评分极低，当前排名可能因 DP 噪声而异常提升，请谨慎参考。
                                </p>
                              )}
                              <p>推荐结果仅作为临床参考，具体用药请遵医嘱。</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
