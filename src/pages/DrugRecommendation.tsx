import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Stethoscope,
  Brain,
  AlertTriangle,
  CheckCircle2,
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
import { usePatientStore } from '@/lib/patientStore'
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
}

interface RecommendationResultItem {
  drugId: number
  drugName: string
  dosage: string
  frequency: string
  confidence: number
  score: number
  dpNoise?: number | null
  reason: string
  interactions: string[]
  sideEffects: string[]
  category: string
  explanation: RecommendationExplanation
}

interface GenerateResponse {
  recommendationId: number
  selected: RecommendationResultItem[]
  base: RecommendationResultItem[]
  dp: RecommendationResultItem[]
  dpEnabled: boolean
}

interface DrugResult {
  id: string
  drugName: string
  dosage: string
  frequency: string
  confidence: number
  reason: string
  interactions: string[]
  sideEffects: string[]
  category: string
  explanation: RecommendationExplanation
}

interface PatientData {
  age: string
  gender: string
  diseases: string
  symptoms: string
  allergies: string
  currentMedications: string
}

export default function DrugRecommendation() {
  const { config, budget, refresh } = usePrivacyStore()
  const { patients } = usePatientStore()
  const location = useLocation()

  const [patientData, setPatientData] = useState<PatientData>({
    age: '',
    gender: '男',
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

  const handleSelectPatient = (id: string) => {
    setSelectedPatientId(id)
    if (!id) return

    const patient = patients.find((item) => item.id === id)
    if (!patient) return

    setPatientData({
      age: String(patient.age),
      gender: patient.gender,
      diseases: patient.chronicDiseases.join('，'),
      symptoms: patient.medicalHistory,
      allergies: patient.allergies.join('，'),
      currentMedications: patient.currentMedications.join('，'),
    })
  }

  const handleAnalyze = async () => {
    setAnalyzeError(null)
    setIsAnalyzing(true)

    try {
      const response = await api.post<GenerateResponse>('/api/recommendations/generate', {
        patientId: selectedPatientId ? Number(selectedPatientId) : undefined,
        age: patientData.age || undefined,
        gender: patientData.gender || undefined,
        diseases: patientData.diseases || undefined,
        symptoms: patientData.symptoms || undefined,
        allergies: patientData.allergies || undefined,
        currentMedications: patientData.currentMedications || undefined,
        dpEnabled,
        topK: 4,
      })

      setComparison({ base: response.base, dp: response.dp })
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
        }))
      )
      setShowResults(true)
      setSelectedDrug(null)
      setShowExplainability(false)
      await refresh()
    } catch (error) {
      setAnalyzeError(getErrorMessage(error, '智能分析失败，请稍后重试'))
      setShowResults(false)
      setSelectedDrug(null)
      setRecommendations([])
      setComparison(null)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600 dark:text-green-400'
    if (confidence >= 80) return 'text-blue-600 dark:text-blue-400'
    return 'text-yellow-600 dark:text-yellow-400'
  }

  const getConfidenceBg = (confidence: number) => {
    if (confidence >= 90) return 'bg-green-500'
    if (confidence >= 80) return 'bg-blue-500'
    return 'bg-yellow-500'
  }

  const noiseScale = useMemo(() => {
    if (config.noiseMechanism === 'gaussian') return gaussianSigma(config)
    return laplaceScale(config)
  }, [config])

  const handlePrint = () => {
    window.print()
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
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600" />
        <div className="absolute inset-0 bg-medical-dna opacity-20" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-cyan-400/20 rounded-full blur-3xl" />

        <div className="relative z-10 px-8 py-10 md:px-12 md:py-14">
          <div className="flex items-start gap-5">
            <div className="hidden md:flex w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm items-center justify-center shadow-xl">
              <Stethoscope className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-bold text-white mb-3 tracking-tight">
                智能用药推荐
              </h1>
              <p className="text-white/70 text-lg max-w-2xl">
                基于深度学习模型的个性化用药建议，融合差分隐私保护技术
              </p>
              <div className="flex flex-wrap gap-3 mt-5">
                {['DeepFM', '注意力机制', '图神经网络', 'DP-SGD'].map((tag, i) => (
                  <span
                    key={tag}
                    className="px-4 py-1.5 rounded-full text-sm font-medium bg-white/10 backdrop-blur-sm text-white border border-white/20"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Input Form */}
        <div className="lg:col-span-2 space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
          >
            <Card className="border-0 shadow-xl overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 dark:from-slate-900 dark:via-slate-800 dark:to-slate-800" />
              <div className="relative z-10">
                <CardHeader className="border-b border-border/50 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
                      <FileText className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <CardTitle className="text-xl">患者信息录入</CardTitle>
                      <CardDescription>填写患者临床信息以获取个性化推荐</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6 pt-6">

                  {/* 患者快速选择 */}
                  {patients.length > 0 && (
                    <div className="p-5 rounded-xl bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30 border border-indigo-100 dark:border-indigo-800">
                      <Label htmlFor="quick-select" className="flex items-center gap-2 mb-3 text-sm font-semibold text-indigo-700 dark:text-indigo-300">
                        <Users className="h-4 w-4" />
                        从患者档案快速填充
                      </Label>
                      <select
                        id="quick-select"
                        value={selectedPatientId}
                        onChange={(e) => handleSelectPatient(e.target.value)}
                        className="flex h-12 w-full rounded-xl border border-indigo-200 dark:border-indigo-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm font-medium shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      >
                        <option value="">-- 选择已有患者（可选）--</option>
                        {patients.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} · {p.gender} · {p.age}岁 · {p.chronicDiseases.slice(0, 2).join('、')}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="age">年龄</Label>
                  <Input
                    id="age"
                    type="number"
                    value={patientData.age}
                    onChange={(e) => setPatientData({ ...patientData, age: e.target.value })}
                    placeholder="例如：45"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gender">性别</Label>
                  <select
                    id="gender"
                    value={patientData.gender}
                    onChange={(e) => setPatientData({ ...patientData, gender: e.target.value })}
                    className="flex h-11 w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="男">男</option>
                    <option value="女">女</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="diseases">确诊疾病（逗号分隔）</Label>
                <Input
                  id="diseases"
                  value={patientData.diseases}
                  onChange={(e) => setPatientData({ ...patientData, diseases: e.target.value })}
                  placeholder="例如：2 型糖尿病，高血压，高脂血症"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="symptoms">主要症状</Label>
                <textarea
                  id="symptoms"
                  value={patientData.symptoms}
                  onChange={(e) => setPatientData({ ...patientData, symptoms: e.target.value })}
                  className="flex min-h-[100px] w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                  placeholder="描述患者当前主要症状、体征等"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="allergies">过敏史</Label>
                  <Input
                    id="allergies"
                    value={patientData.allergies}
                    onChange={(e) => setPatientData({ ...patientData, allergies: e.target.value })}
                    placeholder="例如：青霉素，磺胺类"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currentMedications">当前用药</Label>
                  <Input
                    id="currentMedications"
                    value={patientData.currentMedications}
                    onChange={(e) => setPatientData({ ...patientData, currentMedications: e.target.value })}
                    placeholder="例如：二甲双胍，氨氯地平"
                  />
                </div>
              </div>

              {/* Privacy Level Control */}
              <div className="pt-4 border-t border-border">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <Label className="text-base flex items-center gap-2">
                      <Shield className="h-4 w-4 text-primary" />
                      差分隐私推理开关
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      关闭后展示「无 DP」基线结果；开启后对药物评分注入噪声，并记录隐私预算消耗。
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDpEnabled((v) => !v)}
                    className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      dpEnabled
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'bg-background text-foreground border-border hover:bg-muted'
                    }`}
                  >
                    {dpEnabled ? '已开启' : '已关闭'}
                  </button>
                </div>

                <div className="grid md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground">当前 ε</div>
                    <div className="text-lg font-semibold text-primary">{config.epsilon.toFixed(3)}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground">噪声规模</div>
                    <div className="text-lg font-semibold">
                      {config.noiseMechanism === 'gaussian' ? 'σ' : 'b'} = {noiseScale.toFixed(3)}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground">预算剩余</div>
                    <div className="text-lg font-semibold text-secondary">ε_rem = {budget.remaining.toFixed(2)}</div>
                  </div>
                </div>
              </div>

              {analyzeError && (
                <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                  {analyzeError}
                </div>
              )}

              <Button
                onClick={handleAnalyze}
                className="w-full gap-2 shadow-lg hover:shadow-xl"
                size="lg"
                disabled={isAnalyzing || !patientData.diseases}
              >
                {isAnalyzing ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>正在分析中...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5" />
                    <span>开始智能推荐</span>
                  </>
                )}
              </Button>
            </CardContent>
          </div>
          </Card>
        </motion.div>
      </div>

      {/* Privacy Metrics Sidebar */}
        <div className="space-y-6">
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg sticky top-24">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                隐私保护状态
              </CardTitle>
              <CardDescription>当前会话的隐私指标</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Lock className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">差分隐私机制</span>
                </div>
                <div className="text-lg font-semibold mb-1">
                  {dpEnabled ? `${config.noiseMechanism} 扰动` : '未启用 DP（基线）'}
                </div>
                <p className="text-xs text-muted-foreground">
                  注入阶段：{config.applicationStage === 'data' ? '数据层' : config.applicationStage === 'gradient' ? '梯度层' : '模型层'}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Key className="h-4 w-4 text-secondary" />
                  <span className="text-sm font-medium">隐私预算消耗</span>
                </div>
                <div className="text-lg font-semibold mb-1">ε_total = {config.privacyBudget.toFixed(1)}</div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden mt-2">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-500"
                    style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  已消耗 ε = {budget.spent.toFixed(2)} · 剩余 ε = {budget.remaining.toFixed(2)}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="h-4 w-4 text-amber-500" />
                  <span className="text-sm font-medium">噪声规模</span>
                </div>
                <div className="text-lg font-semibold mb-1">
                  {config.noiseMechanism === 'gaussian' ? 'σ' : 'b'} = {noiseScale.toFixed(3)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {config.noiseMechanism === 'gaussian' ? `(ε,δ)-DP · δ=${config.delta.toExponential(2)}` : 'ε-DP（纯 DP）'}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="text-sm font-medium">数据安全</span>
                </div>
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  所有计算均在加密环境中进行
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Results Section */}
      <AnimatePresence>
        {showResults && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            transition={{ duration: 0.5 }}
            className="print-area"
          >
            <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-secondary/5 to-purple-50 dark:from-primary/10 dark:via-secondary/10 dark:to-purple-950/30 shadow-xl">
              <CardHeader>
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg">
                      <Stethoscope className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <CardTitle>推荐结果</CardTitle>
                      <CardDescription>
                        基于深度学习模型分析，为您生成以下个性化用药建议
                      </CardDescription>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="gap-2 no-print" onClick={handlePrint}>
                    <Printer className="h-4 w-4" />
                    打印 / 导出
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* DP 对比 */}
                {comparison && (
                  <div className="mb-6 p-4 rounded-xl bg-background border border-border">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <GitCompare className="h-4 w-4 text-primary" />
                        <span className="text-sm font-medium">有/无 DP 结果对比（Top-4）</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {dpEnabled ? '当前展示：DP 结果' : '当前展示：基线结果'}
                      </div>
                    </div>
                    <div className="grid md:grid-cols-2 gap-3 mt-3 text-sm">
                      <div className="p-3 rounded-lg bg-muted/40 border border-border">
                        <div className="text-xs text-muted-foreground mb-2">无 DP（基线）</div>
                        <ol className="space-y-1">
                          {comparison.base.map((r, idx) => (
                            <li key={r.drugId} className="flex justify-between gap-2">
                              <span className="truncate">{idx + 1}. {r.drugName}</span>
                              <span className="text-muted-foreground">score {r.score.toFixed(2)}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                      <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                        <div className="text-xs text-muted-foreground mb-2">差分隐私（噪声后）</div>
                        <ol className="space-y-1">
                          {comparison.dp.map((r, idx) => (
                            <li key={r.drugId} className="flex justify-between gap-2">
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

                {/* Drug Cards */}
                <div className="grid md:grid-cols-2 gap-4 mb-6">
                  {recommendations.map((rec, index) => (
                    <motion.div
                      key={rec.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.1 }}
                      onClick={() => setSelectedDrug(selectedDrug?.id === rec.id ? null : rec)}
                      className={`p-5 rounded-xl border-2 cursor-pointer transition-all duration-300 ${
                        selectedDrug?.id === rec.id
                          ? 'border-primary bg-primary/5 shadow-lg scale-[1.02]'
                          : 'border-border hover:border-primary/50 hover:shadow-md'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Pill className="h-5 w-5 text-primary" />
                            <h4 className="font-semibold text-lg">{rec.drugName}</h4>
                          </div>
                          <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                            {rec.category}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className={`text-2xl font-bold ${getConfidenceColor(rec.confidence)}`}>
                            {rec.confidence}%
                          </div>
                          <div className="text-xs text-muted-foreground">置信度</div>
                        </div>
                      </div>

                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Target className="h-4 w-4" />
                          <span>{rec.dosage} · {rec.frequency}</span>
                        </div>
                      </div>

                      <div className="mt-4">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground">推荐强度</span>
                          <span className={getConfidenceColor(rec.confidence)}>{rec.confidence}%</span>
                        </div>
                        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${rec.confidence}%` }}
                            transition={{ delay: 0.5 + index * 0.1, duration: 0.8 }}
                            className={`h-full ${getConfidenceBg(rec.confidence)}`}
                          />
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>

                {/* Detailed Drug Information */}
                {selectedDrug && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="border-t border-border pt-6"
                  >
                    <div className="bg-background rounded-xl p-6 border border-border space-y-6">
                      <h4 className="font-semibold text-lg flex items-center gap-2">
                        <Info className="h-5 w-5 text-primary" />
                        详细用药说明 — {selectedDrug.drugName}
                      </h4>

                      <div className="grid md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <TrendingUp className="h-4 w-4 text-primary" />
                              推荐理由
                            </h5>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                              {selectedDrug.reason}
                            </p>
                          </div>

                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <Clock className="h-4 w-4 text-secondary" />
                              用法用量
                            </h5>
                            <div className="p-3 rounded-lg bg-secondary/5 border border-secondary/20">
                              <p className="text-sm"><strong>剂量：</strong>{selectedDrug.dosage}</p>
                              <p className="text-sm"><strong>频率：</strong>{selectedDrug.frequency}</p>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-4">
                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-amber-500" />
                              药物相互作用
                            </h5>
                            <div className="space-y-2">
                              {selectedDrug.interactions.map((interaction, i) => (
                                <div key={i} className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                                  <p className="text-sm text-amber-800 dark:text-amber-200">{interaction}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <Info className="h-4 w-4 text-blue-500" />
                              常见副作用
                            </h5>
                            <div className="flex flex-wrap gap-2">
                              {selectedDrug.sideEffects.map((effect, i) => (
                                <span key={i} className="px-3 py-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-sm border border-blue-200 dark:border-blue-800">
                                  {effect}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Safety Warnings */}
                      {selectedDrug.explanation.warnings.length > 0 && (
                        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                          <h5 className="font-medium mb-2 flex items-center gap-2 text-red-700 dark:text-red-300">
                            <AlertTriangle className="h-4 w-4" />
                            安全警示
                          </h5>
                          <ul className="space-y-1">
                            {selectedDrug.explanation.warnings.map((w, i) => (
                              <li key={i} className="text-sm text-red-600 dark:text-red-400 flex items-start gap-2">
                                <span className="mt-1">•</span>
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
                          className="flex items-center gap-2 text-sm font-medium text-primary hover:underline mb-3"
                        >
                          <Brain className="h-4 w-4" />
                          模型可解释性分析
                          {showExplainability ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </button>

                        <AnimatePresence>
                          {showExplainability && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="p-4 rounded-xl bg-gradient-to-br from-primary/3 to-secondary/3 border border-primary/10">
                                <p className="text-xs text-muted-foreground mb-4">
                                  以下展示深度学习模型各特征维度对本次推荐评分的贡献（基于 DeepFM 注意力权重分析）
                                </p>
                                <div className="h-[240px]">
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
                                      <XAxis type="number" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 11 }} />
                                      <YAxis
                                        dataKey="name"
                                        type="category"
                                        width={110}
                                        stroke="hsl(var(--muted-foreground))"
                                        tick={{ fontSize: 11 }}
                                      />
                                      <Tooltip
                                        contentStyle={{
                                          backgroundColor: 'hsl(var(--card))',
                                          border: '1px solid hsl(var(--border))',
                                          borderRadius: '8px',
                                          fontSize: '12px',
                                        }}
                                        formatter={(v: number) => [v.toFixed(3), '贡献值']}
                                      />
                                      <Bar dataKey="contribution" name="特征贡献" radius={[0, 4, 4, 0]}>
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
                                <p className="text-xs text-muted-foreground mt-3">
                                  正值（蓝色）表示该特征增强推荐，负值（红色）表示该特征降低推荐评分（如过敏、禁忌）
                                </p>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>

                      {/* Privacy Notice */}
                      <div className="pt-4 border-t border-border">
                        <div className="flex items-start gap-3 p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
                          <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <h5 className="font-medium text-blue-800 dark:text-blue-300 mb-1">
                              隐私保护说明
                            </h5>
                            <p className="text-sm text-blue-700 dark:text-blue-400">
                              本次推荐{dpEnabled ? '在差分隐私保护下生成' : '以无 DP 基线方式生成'}（ε = {config.epsilon.toFixed(3)}），
                              {dpEnabled ? '推荐评分已注入随机噪声以降低推断风险。' : '未注入噪声，仅用于对比展示。'}
                              推荐结果仅作为临床参考，具体用药请遵医嘱。
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
