import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
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
    if (confidence >= 90) return 'text-ia-data-3'
    if (confidence >= 80) return 'text-primary'
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
      {/* Page Header — Border-left editorial */}
      <section className="border-l-4 border-l-primary bg-card px-6 py-8">
        <div className="flex items-start gap-4">
          <div className="hidden md:flex h-10 w-10 items-center justify-center rounded-standard bg-primary flex-shrink-0">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
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
                <div className="flex h-9 w-9 items-center justify-center rounded-standard bg-primary">
                  <FileText className="h-4 w-4 text-primary-foreground" />
                </div>
                <div>
                  <CardTitle>患者信息录入</CardTitle>
                  <CardDescription>填写患者临床信息以获取个性化推荐</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Patient quick select */}
              {patients.length > 0 && (
                <div className="p-3 rounded-standard bg-muted border border-ia-border">
                  <Label htmlFor="quick-select" className="flex items-center gap-2 mb-2 text-ia-caption font-heading font-semibold">
                    <Users className="h-3.5 w-3.5 text-primary" />
                    从患者档案快速填充
                  </Label>
                  <select
                    id="quick-select"
                    value={selectedPatientId}
                    onChange={(e) => handleSelectPatient(e.target.value)}
                    className="flex h-10 w-full rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary"
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
                <div className="space-y-1.5">
                  <Label htmlFor="age" className="text-ia-caption font-heading font-semibold">年龄</Label>
                  <Input id="age" type="number" value={patientData.age} onChange={(e) => setPatientData({ ...patientData, age: e.target.value })} placeholder="例如：45" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="gender" className="text-ia-caption font-heading font-semibold">性别</Label>
                  <select
                    id="gender"
                    value={patientData.gender}
                    onChange={(e) => setPatientData({ ...patientData, gender: e.target.value })}
                    className="flex h-10 w-full rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary"
                  >
                    <option value="男">男</option>
                    <option value="女">女</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="diseases" className="text-ia-caption font-heading font-semibold">确诊疾病（逗号分隔）</Label>
                <Input id="diseases" value={patientData.diseases} onChange={(e) => setPatientData({ ...patientData, diseases: e.target.value })} placeholder="例如：2 型糖尿病，高血压，高脂血症" />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="symptoms" className="text-ia-caption font-heading font-semibold">主要症状</Label>
                <textarea
                  id="symptoms"
                  value={patientData.symptoms}
                  onChange={(e) => setPatientData({ ...patientData, symptoms: e.target.value })}
                  className="flex min-h-[80px] w-full rounded-standard border border-ia-border bg-card px-3 py-2 text-ia-body font-body placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:border-primary focus-visible:ring-1 focus-visible:ring-primary resize-none"
                  placeholder="描述患者当前主要症状、体征等"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="allergies" className="text-ia-caption font-heading font-semibold">过敏史</Label>
                  <Input id="allergies" value={patientData.allergies} onChange={(e) => setPatientData({ ...patientData, allergies: e.target.value })} placeholder="例如：青霉素，磺胺类" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="currentMedications" className="text-ia-caption font-heading font-semibold">当前用药</Label>
                  <Input id="currentMedications" value={patientData.currentMedications} onChange={(e) => setPatientData({ ...patientData, currentMedications: e.target.value })} placeholder="例如：二甲双胍，氨氯地平" />
                </div>
              </div>

              {/* Privacy Level Control */}
              <div className="pt-4 border-t border-ia-border">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <Label className="text-ia-caption font-heading font-semibold flex items-center gap-2">
                      <Shield className="h-3.5 w-3.5 text-primary" />
                      差分隐私推理开关
                    </Label>
                    <p className="text-ia-label text-muted-foreground mt-1">
                      关闭后展示「无 DP」基线结果；开启后对药物评分注入噪声，并记录隐私预算消耗。
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDpEnabled((v) => !v)}
                    className={`px-3 py-1.5 rounded-standard border text-ia-caption font-heading font-semibold transition-colors duration-150 cursor-pointer ${
                      dpEnabled
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'bg-card text-foreground border-ia-border hover:bg-muted'
                    }`}
                  >
                    {dpEnabled ? '已开启' : '已关闭'}
                  </button>
                </div>

                <div className="grid md:grid-cols-3 gap-2">
                  <div className="p-2.5 rounded-standard bg-muted border border-ia-border">
                    <div className="text-ia-label text-muted-foreground">当前 ε</div>
                    <div className="text-ia-body font-heading font-bold text-primary">{config.epsilon.toFixed(3)}</div>
                  </div>
                  <div className="p-2.5 rounded-standard bg-muted border border-ia-border">
                    <div className="text-ia-label text-muted-foreground">噪声规模</div>
                    <div className="text-ia-body font-heading font-bold">
                      {config.noiseMechanism === 'gaussian' ? 'σ' : 'b'} = {noiseScale.toFixed(3)}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-standard bg-muted border border-ia-border">
                    <div className="text-ia-label text-muted-foreground">预算剩余</div>
                    <div className="text-ia-body font-heading font-bold text-secondary">ε_rem = {budget.remaining.toFixed(2)}</div>
                  </div>
                </div>
              </div>

              {analyzeError && (
                <div className="rounded-standard border border-destructive/30 bg-destructive/6 p-2.5 text-ia-caption text-destructive">
                  {analyzeError}
                </div>
              )}

              <Button
                onClick={handleAnalyze}
                className="w-full gap-2"
                size="lg"
                loading={isAnalyzing}
                disabled={isAnalyzing || !patientData.diseases}
              >
                <Sparkles className="h-4 w-4" />
                开始智能推荐
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right: Privacy panel */}
        <div className="space-y-6">
          <Card hover="none" className="sticky top-20">
            <div className="h-0.5 bg-primary" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield className="h-4 w-4 text-primary" />
                隐私保护状态
              </CardTitle>
              <CardDescription>当前会话的隐私指标</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-3 rounded-standard bg-muted border border-ia-border">
                <div className="flex items-center gap-2 mb-1.5">
                  <Lock className="h-3.5 w-3.5 text-primary" />
                  <span className="text-ia-caption font-heading font-semibold">差分隐私机制</span>
                </div>
                <div className="text-ia-body font-heading font-bold">
                  {dpEnabled ? `${config.noiseMechanism} 扰动` : '未启用 DP（基线）'}
                </div>
                <p className="text-ia-label text-muted-foreground">
                  注入阶段：{config.applicationStage === 'data' ? '数据层' : config.applicationStage === 'gradient' ? '梯度层' : '模型层'}
                </p>
              </div>

              <div className="p-3 rounded-standard bg-muted border border-ia-border">
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

              <div className="p-3 rounded-standard bg-muted border border-ia-border">
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

              <div className="p-3 rounded-standard border border-ia-data-3/30 bg-ia-data-3/6">
                <div className="flex items-center gap-2 text-ia-data-3">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span className="text-ia-caption font-heading font-semibold">数据安全</span>
                </div>
                <p className="text-ia-label text-ia-data-3/80 mt-1">
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
          <div className="animate-fade-in print-area">
            <Card hover="none" className="border-primary/20">
              <CardHeader>
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-standard bg-primary">
                      <Stethoscope className="h-4 w-4 text-primary-foreground" />
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
                  <div className="mb-5 p-3 rounded-standard bg-muted border border-ia-border">
                    <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
                      <div className="flex items-center gap-2">
                        <GitCompare className="h-3.5 w-3.5 text-primary" />
                        <span className="text-ia-caption font-heading font-semibold">有/无 DP 结果对比（Top-4）</span>
                      </div>
                      <div className="text-ia-label text-muted-foreground">
                        {dpEnabled ? '当前展示：DP 结果' : '当前展示：基线结果'}
                      </div>
                    </div>
                    <div className="grid md:grid-cols-2 gap-2 text-ia-caption">
                      <div className="p-2.5 rounded-standard bg-card border border-ia-border">
                        <div className="text-ia-label text-muted-foreground mb-1.5">无 DP（基线）</div>
                        <ol className="space-y-0.5">
                          {comparison.base.map((r, idx) => (
                            <li key={r.drugId} className="flex justify-between gap-2">
                              <span className="truncate">{idx + 1}. {r.drugName}</span>
                              <span className="text-muted-foreground">score {r.score.toFixed(2)}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                      <div className="p-2.5 rounded-standard border border-primary/20 bg-primary/4">
                        <div className="text-ia-label text-muted-foreground mb-1.5">差分隐私（噪声后）</div>
                        <ol className="space-y-0.5">
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
                <div className="grid md:grid-cols-2 gap-3 mb-5">
                  {recommendations.map((rec) => (
                    <div
                      key={rec.id}
                      onClick={() => setSelectedDrug(selectedDrug?.id === rec.id ? null : rec)}
                      className={`p-4 rounded-standard border cursor-pointer transition-colors duration-150 bg-card ${
                        selectedDrug?.id === rec.id
                          ? 'border-primary ia-border-3'
                          : 'border-ia-border hover:border-primary/40'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <Pill className="h-4 w-4 text-primary" />
                            <h4 className="font-heading font-semibold text-ia-card-title">{rec.drugName}</h4>
                          </div>
                          <span className="ia-badge ia-badge-primary">
                            {rec.category}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className={`text-xl font-heading font-bold ${getConfidenceColor(rec.confidence)}`}>
                            {rec.confidence}%
                          </div>
                          <div className="text-ia-label text-muted-foreground">置信度</div>
                        </div>
                      </div>

                      <div className="text-ia-caption text-muted-foreground flex items-center gap-2">
                        <Target className="h-3.5 w-3.5" />
                        <span>{rec.dosage} · {rec.frequency}</span>
                      </div>

                      <div className="mt-3">
                        <div className="progress-bar">
                          <div
                            className="progress-bar-fill"
                            style={{ width: `${rec.confidence}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Detailed Drug Information */}
                {selectedDrug && (
                  <div className="border-t border-ia-border pt-5">
                    <div className="p-5 rounded-standard bg-muted border border-ia-border space-y-5">
                      <h4 className="font-heading font-semibold text-ia-card-title flex items-center gap-2">
                        <Info className="h-4 w-4 text-primary" />
                        详细用药说明 — {selectedDrug.drugName}
                      </h4>

                      <div className="grid md:grid-cols-2 gap-5">
                        <div className="space-y-4">
                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <TrendingUp className="h-3.5 w-3.5 text-primary" />
                              推荐理由
                            </h5>
                            <TextExpander text={selectedDrug.reason} maxLines={3} expandText="查看完整理由" collapseText="收起理由" />
                          </div>

                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <Clock className="h-3.5 w-3.5 text-secondary" />
                              用法用量
                            </h5>
                            <div className="p-2.5 rounded-standard bg-card border border-ia-border">
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
                                <div key={i} className="p-2.5 rounded-standard border border-ia-data-4/30 bg-ia-data-4/6">
                                  <p className="text-ia-caption text-ia-data-4">{interaction}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2">
                              <Info className="h-3.5 w-3.5 text-primary" />
                              常见副作用
                            </h5>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedDrug.sideEffects.map((effect, i) => (
                                <span key={i} className="ia-badge ia-badge-primary">
                                  {effect}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Safety Warnings */}
                      {selectedDrug.explanation.warnings.length > 0 && (
                        <div className="p-3 rounded-standard border border-destructive/30 bg-destructive/6">
                          <h5 className="font-heading font-semibold text-ia-caption mb-2 flex items-center gap-2 text-destructive">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            安全警示
                          </h5>
                          <ul className="space-y-1">
                            {selectedDrug.explanation.warnings.map((w, i) => (
                              <li key={i} className="text-ia-caption text-destructive flex items-start gap-2">
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
                          className="flex items-center gap-2 text-ia-caption font-heading font-semibold text-primary hover:underline cursor-pointer mb-3"
                        >
                          <Brain className="h-3.5 w-3.5" />
                          模型可解释性分析
                          {showExplainability ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>

                        <AnimatePresence>
                          {showExplainability && (
                            <div className="animate-fade-in overflow-hidden">
                              <div className="p-4 rounded-standard bg-card border border-ia-border">
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
                      <div className="pt-4 border-t border-ia-border">
                        <div className="flex items-start gap-3 p-3 rounded-standard border border-primary/20 bg-primary/4">
                          <Shield className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                          <div>
                            <h5 className="font-heading font-semibold text-ia-caption mb-1 text-primary">
                              隐私保护说明
                            </h5>
                            <p className="text-ia-caption text-muted-foreground">
                              本次推荐{dpEnabled ? '在差分隐私保护下生成' : '以无 DP 基线方式生成'}（ε = {config.epsilon.toFixed(3)}），
                              {dpEnabled ? '推荐评分已注入随机噪声以降低推断风险。' : '未注入噪声，仅用于对比展示。'}
                              推荐结果仅作为临床参考，具体用药请遵医嘱。
                            </p>
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
