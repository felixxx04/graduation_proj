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

  useEffect(() => {
    const state = location.state as { prefill?: Partial<PatientData> } | null
    if (!state?.prefill) return
    setPatientData((prev) => ({ ...prev, ...state.prefill }))
    window.history.replaceState({}, '')
  }, [location.state])

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
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-2">
          鏅鸿兘鐢ㄨ嵂鎺ㄨ崘
        </h1>
        <p className="text-muted-foreground">
          鍩轰簬娣卞害瀛︿範妯″瀷鐨勪釜鎬у寲鐢ㄨ嵂寤鸿锛岃瀺鍚堝樊鍒嗛殣绉佷繚鎶ゆ妧鏈?
        </p>
      </div>

      {/* Algorithm Info Banner */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center flex-shrink-0 shadow-md">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                娣卞害瀛︿範鎺ㄨ崘绠楁硶
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed mb-3">
                鏈郴缁熼噰鐢?strong>娣卞害鍥犲瓙鍒嗚В鏈?(DeepFM)</strong> 鏋舵瀯锛岀粨鍚?strong>娉ㄦ剰鍔涙満鍒?/strong>鍜?strong>鍥剧缁忕綉缁?/strong>锛?
                瀵规偅鑰呯壒寰併€佺柧鐥呮ā寮忋€佽嵂鐗╃壒鎬ц繘琛屽缁村缓妯°€傛ā鍨嬪湪璁粌杩囩▼涓瀺鍏?strong>宸垎闅愮姊害鎵板姩</strong>锛?
                纭繚鎮ｈ€呮暟鎹殣绉佸畨鍏ㄣ€?
              </p>
              <div className="flex flex-wrap gap-2">
                {['DeepFM 妯″瀷', '娉ㄦ剰鍔涙満鍒?, '鍥剧缁忕綉缁?, '宸垎闅愮 SGD'].map((tag, i) => (
                  <span key={tag} className={`px-3 py-1 rounded-full text-xs font-medium ${
                    i === 0 ? 'bg-primary/10 text-primary' :
                    i === 1 ? 'bg-secondary/10 text-secondary' :
                    i === 2 ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400' :
                    'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                  }`}>{tag}</span>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Input Form */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>鎮ｈ€呬俊鎭綍鍏?/CardTitle>
                  <CardDescription>濉啓鎮ｈ€呬复搴婁俊鎭互鑾峰彇涓€у寲鎺ㄨ崘</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">

              {/* 鎮ｈ€呭揩閫熼€夋嫨 */}
              {patients.length > 0 && (
                <div className="p-4 rounded-xl bg-gradient-to-br from-secondary/5 to-primary/5 border border-secondary/20">
                  <Label htmlFor="quick-select" className="flex items-center gap-2 mb-2 text-sm font-medium">
                    <Users className="h-4 w-4 text-secondary" />
                    浠庢偅鑰呮。妗堝揩閫熷～鍏?
                  </Label>
                  <select
                    id="quick-select"
                    value={selectedPatientId}
                    onChange={(e) => handleSelectPatient(e.target.value)}
                    className="flex h-11 w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="">-- 閫夋嫨宸叉湁鎮ｈ€咃紙鍙€夛級--</option>
                    {patients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} 路 {p.gender} 路 {p.age}宀?路 {p.chronicDiseases.slice(0, 2).join('銆?)}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-muted-foreground mt-1.5">閫夋嫨鍚庤嚜鍔ㄥ～鍏呬笅鏂硅〃鍗曞瓧娈碉紝涔熷彲鎵嬪姩淇敼</p>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="age">骞撮緞</Label>
                  <Input
                    id="age"
                    type="number"
                    value={patientData.age}
                    onChange={(e) => setPatientData({ ...patientData, age: e.target.value })}
                    placeholder="渚嬪锛?5"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gender">鎬у埆</Label>
                  <select
                    id="gender"
                    value={patientData.gender}
                    onChange={(e) => setPatientData({ ...patientData, gender: e.target.value })}
                    className="flex h-11 w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="鐢?>鐢?/option>
                    <option value="濂?>濂?/option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="diseases">纭瘖鐤剧梾锛堥€楀彿鍒嗛殧锛?/Label>
                <Input
                  id="diseases"
                  value={patientData.diseases}
                  onChange={(e) => setPatientData({ ...patientData, diseases: e.target.value })}
                  placeholder="渚嬪锛? 鍨嬬硸灏跨梾锛岄珮琛€鍘嬶紝楂樿剛琛€鐥?
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="symptoms">涓昏鐥囩姸</Label>
                <textarea
                  id="symptoms"
                  value={patientData.symptoms}
                  onChange={(e) => setPatientData({ ...patientData, symptoms: e.target.value })}
                  className="flex min-h-[100px] w-full rounded-lg border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                  placeholder="鎻忚堪鎮ｈ€呭綋鍓嶄富瑕佺棁鐘躲€佷綋寰佺瓑"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="allergies">杩囨晱鍙?/Label>
                  <Input
                    id="allergies"
                    value={patientData.allergies}
                    onChange={(e) => setPatientData({ ...patientData, allergies: e.target.value })}
                    placeholder="渚嬪锛氶潚闇夌礌锛岀：鑳虹被"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currentMedications">褰撳墠鐢ㄨ嵂</Label>
                  <Input
                    id="currentMedications"
                    value={patientData.currentMedications}
                    onChange={(e) => setPatientData({ ...patientData, currentMedications: e.target.value })}
                    placeholder="渚嬪锛氫簩鐢插弻鑳嶏紝姘ㄦ隘鍦板钩"
                  />
                </div>
              </div>

              {/* Privacy Level Control */}
              <div className="pt-4 border-t border-border">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <Label className="text-base flex items-center gap-2">
                      <Shield className="h-4 w-4 text-primary" />
                      宸垎闅愮鎺ㄧ悊寮€鍏?
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      鍏抽棴鍚庡睍绀恒€屾棤 DP銆嶅熀绾跨粨鏋滐紱寮€鍚悗瀵硅嵂鐗╄瘎鍒嗘敞鍏ュ櫔澹帮紝骞惰褰曢殣绉侀绠楁秷鑰椼€?
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
                    {dpEnabled ? '宸插紑鍚? : '宸插叧闂?}
                  </button>
                </div>

                <div className="grid md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground">褰撳墠 蔚</div>
                    <div className="text-lg font-semibold text-primary">{config.epsilon.toFixed(3)}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground">鍣０瑙勬ā</div>
                    <div className="text-lg font-semibold">
                      {config.noiseMechanism === 'gaussian' ? '蟽' : 'b'} = {noiseScale.toFixed(3)}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground">棰勭畻鍓╀綑</div>
                    <div className="text-lg font-semibold text-secondary">蔚_rem = {budget.remaining.toFixed(2)}</div>
                  </div>
                </div>
              </div>
              {analyzeError && (
                <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                  {analyzeError}
                </div>
              )}

              <Button
                onClick={handleAnalyze}                className="w-full gap-2 shadow-lg hover:shadow-xl"
                size="lg"
                disabled={isAnalyzing || !patientData.diseases}
              >
                {isAnalyzing ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>姝ｅ湪鍒嗘瀽涓?..</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5" />
                    <span>寮€濮嬫櫤鑳芥帹鑽?/span>
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Privacy Metrics Sidebar */}
        <div className="space-y-6">
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg sticky top-24">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                闅愮淇濇姢鐘舵€?
              </CardTitle>
              <CardDescription>褰撳墠浼氳瘽鐨勯殣绉佹寚鏍?/CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Lock className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">宸垎闅愮鏈哄埗</span>
                </div>
                <div className="text-lg font-semibold mb-1">
                  {dpEnabled ? `${config.noiseMechanism} 鎵板姩` : '鏈惎鐢?DP锛堝熀绾匡級'}
                </div>
                <p className="text-xs text-muted-foreground">
                  娉ㄥ叆闃舵锛歿config.applicationStage === 'data' ? '鏁版嵁灞? : config.applicationStage === 'gradient' ? '姊害灞? : '妯″瀷灞?}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Key className="h-4 w-4 text-secondary" />
                  <span className="text-sm font-medium">闅愮棰勭畻娑堣€?/span>
                </div>
                <div className="text-lg font-semibold mb-1">蔚_total = {config.privacyBudget.toFixed(1)}</div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden mt-2">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-500"
                    style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  宸叉秷鑰?蔚 = {budget.spent.toFixed(2)} 路 鍓╀綑 蔚 = {budget.remaining.toFixed(2)}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="h-4 w-4 text-amber-500" />
                  <span className="text-sm font-medium">鍣０瑙勬ā</span>
                </div>
                <div className="text-lg font-semibold mb-1">
                  {config.noiseMechanism === 'gaussian' ? '蟽' : 'b'} = {noiseScale.toFixed(3)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {config.noiseMechanism === 'gaussian' ? `(蔚,未)-DP 路 未=${config.delta.toExponential(2)}` : '蔚-DP锛堢函 DP锛?}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="text-sm font-medium">鏁版嵁瀹夊叏</span>
                </div>
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  鎵€鏈夎绠楀潎鍦ㄥ姞瀵嗙幆澧冧腑杩涜
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
                      <CardTitle>鎺ㄨ崘缁撴灉</CardTitle>
                      <CardDescription>
                        鍩轰簬娣卞害瀛︿範妯″瀷鍒嗘瀽锛屼负鎮ㄧ敓鎴愪互涓嬩釜鎬у寲鐢ㄨ嵂寤鸿
                      </CardDescription>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="gap-2 no-print" onClick={handlePrint}>
                    <Printer className="h-4 w-4" />
                    鎵撳嵃 / 瀵煎嚭
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* DP 瀵规瘮 */}
                {comparison && (
                  <div className="mb-6 p-4 rounded-xl bg-background border border-border">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <GitCompare className="h-4 w-4 text-primary" />
                        <span className="text-sm font-medium">鏈?鏃?DP 缁撴灉瀵规瘮锛圱op-4锛?/span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {dpEnabled ? '褰撳墠灞曠ず锛欴P 缁撴灉' : '褰撳墠灞曠ず锛氬熀绾跨粨鏋?}
                      </div>
                    </div>
                    <div className="grid md:grid-cols-2 gap-3 mt-3 text-sm">
                      <div className="p-3 rounded-lg bg-muted/40 border border-border">
                        <div className="text-xs text-muted-foreground mb-2">鏃?DP锛堝熀绾匡級</div>
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
                        <div className="text-xs text-muted-foreground mb-2">宸垎闅愮锛堝櫔澹板悗锛?/div>
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
                          <div className="text-xs text-muted-foreground">缃俊搴?/div>
                        </div>
                      </div>

                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Target className="h-4 w-4" />
                          <span>{rec.dosage} 路 {rec.frequency}</span>
                        </div>
                      </div>

                      <div className="mt-4">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground">鎺ㄨ崘寮哄害</span>
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
                        璇︾粏鐢ㄨ嵂璇存槑 鈥?{selectedDrug.drugName}
                      </h4>

                      <div className="grid md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <TrendingUp className="h-4 w-4 text-primary" />
                              鎺ㄨ崘鐞嗙敱
                            </h5>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                              {selectedDrug.reason}
                            </p>
                          </div>

                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <Clock className="h-4 w-4 text-secondary" />
                              鐢ㄦ硶鐢ㄩ噺
                            </h5>
                            <div className="p-3 rounded-lg bg-secondary/5 border border-secondary/20">
                              <p className="text-sm"><strong>鍓傞噺锛?/strong>{selectedDrug.dosage}</p>
                              <p className="text-sm"><strong>棰戠巼锛?/strong>{selectedDrug.frequency}</p>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-4">
                          <div>
                            <h5 className="font-medium mb-2 flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-amber-500" />
                              鑽墿鐩镐簰浣滅敤
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
                              甯歌鍓綔鐢?
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
                            瀹夊叏璀︾ず
                          </h5>
                          <ul className="space-y-1">
                            {selectedDrug.explanation.warnings.map((w, i) => (
                              <li key={i} className="text-sm text-red-600 dark:text-red-400 flex items-start gap-2">
                                <span className="mt-1">鈥?/span>
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
                          妯″瀷鍙В閲婃€у垎鏋?
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
                                  浠ヤ笅灞曠ず娣卞害瀛︿範妯″瀷鍚勭壒寰佺淮搴﹀鏈鎺ㄨ崘璇勫垎鐨勮础鐚紙鍩轰簬 DeepFM 娉ㄦ剰鍔涙潈閲嶅垎鏋愶級
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
                                        formatter={(v: number) => [v.toFixed(3), '璐＄尞鍊?]}
                                      />
                                      <Bar dataKey="contribution" name="鐗瑰緛璐＄尞" radius={[0, 4, 4, 0]}>
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
                                  姝ｅ€硷紙钃濊壊锛夎〃绀鸿鐗瑰緛澧炲己鎺ㄨ崘锛岃礋鍊硷紙绾㈣壊锛夎〃绀鸿鐗瑰緛闄嶄綆鎺ㄨ崘璇勫垎锛堝杩囨晱銆佺蹇岋級
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
                              闅愮淇濇姢璇存槑
                            </h5>
                            <p className="text-sm text-blue-700 dark:text-blue-400">
                              鏈鎺ㄨ崘{dpEnabled ? '鍦ㄥ樊鍒嗛殣绉佷繚鎶や笅鐢熸垚' : '浠ユ棤 DP 鍩虹嚎鏂瑰紡鐢熸垚'}锛埼?= {config.epsilon.toFixed(3)}锛夛紝
                              {dpEnabled ? '鎺ㄨ崘璇勫垎宸叉敞鍏ラ殢鏈哄櫔澹颁互闄嶄綆鎺ㄦ柇椋庨櫓銆? : '鏈敞鍏ュ櫔澹帮紝浠呯敤浜庡姣斿睍绀恒€?}
                              鎺ㄨ崘缁撴灉浠呬綔涓轰复搴婂弬鑰冿紝鍏蜂綋鐢ㄨ嵂璇烽伒鍖诲槺銆?
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



