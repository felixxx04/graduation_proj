import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Shield, 
  Lock, 
  Settings, 
  Info, 
  CheckCircle2, 
  AlertTriangle,
  TrendingDown,
  Eye,
  Key,
  Sliders,
  BookOpen,
  BarChart3,
  Activity
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Label } from '@/components/ui/label'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { usePrivacyStore } from '@/lib/privacyStore'
import type { PrivacyConfig as GlobalPrivacyConfig } from '@/lib/privacy'
import { gaussianSigma, laplaceScale } from '@/lib/privacy'

export default function PrivacyConfig() {
  const { config: globalConfig, setConfig: setGlobalConfig, budget, clearEvents } = usePrivacyStore()
  const [config, setConfig] = useState<GlobalPrivacyConfig>(globalConfig)

  const [savedConfig, setSavedConfig] = useState<GlobalPrivacyConfig | null>(null)

  // 计算噪声规模
  const calculateNoiseScale = () => {
    if (config.noiseMechanism === 'gaussian') return gaussianSigma(config)
    return laplaceScale(config)
  }

  // 计算隐私保护强度评分
  const calculatePrivacyScore = () => {
    const epsilonScore = Math.max(0, 10 - config.epsilon * 5)
    const deltaScore = config.delta < 0.0001 ? 10 : Math.max(0, 10 - config.delta * 10000)
    return ((epsilonScore + deltaScore) / 2).toFixed(1)
  }

  // 计算效用损失估计
  const estimateUtilityLoss = () => {
    const noiseScale = calculateNoiseScale()
    if (noiseScale === Infinity) return '100.0'
    const loss = Math.min(100, noiseScale * 30)
    return loss.toFixed(1)
  }

  const handleSave = () => {
    setSavedConfig({ ...config })
    setGlobalConfig({ ...config })
  }

  const noiseScale = calculateNoiseScale()
  const privacyScore = calculatePrivacyScore()
  const utilityLoss = estimateUtilityLoss()

  return (
    <div className="space-y-10">
      {/* Hero Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden rounded-2xl"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600" />
        <div className="absolute inset-0 bg-medical-dna opacity-20" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-fuchsia-400/20 rounded-full blur-3xl" />

        <div className="relative z-10 px-8 py-10 md:px-12 md:py-14">
          <div className="flex items-start gap-5">
            <div className="hidden md:flex w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm items-center justify-center shadow-xl">
              <Shield className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-bold text-white mb-3 tracking-tight">
                差分隐私配置
              </h1>
              <p className="text-white/70 text-lg max-w-2xl">
                配置隐私保护参数，在数据安全与模型性能之间寻找最佳平衡点
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Algorithm Explanation */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <BookOpen className="h-6 w-6 text-primary" />
            <CardTitle>差分隐私算法原理</CardTitle>
          </div>
          <CardDescription className="text-base">
            理解核心概念与数学基础
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-background border border-border">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                ε-差分隐私定义
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">
                对于任意两个相邻数据集 D₁ 和 D₂，以及任意输出 S：
                <br />
                <code className="block mt-2 p-2 bg-muted rounded text-xs overflow-x-auto">
                  Pr[M(D₁) ∈ S] ≤ e^ε × Pr[M(D₂) ∈ S] + δ
                </code>
              </p>
            </div>
            <div className="p-4 rounded-lg bg-background border border-border">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <Lock className="h-4 w-4 text-secondary" />
                隐私预算 ε
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">
                ε 越小，隐私保护越强，但数据效用越低。推荐范围：0.1 ~ 10
                <br />
                <span className="text-xs text-muted-foreground mt-1 block">
                  本系统默认 ε = 1.0，提供强隐私保护
                </span>
              </p>
            </div>
          </div>

          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="mechanism">
              <AccordionTrigger>噪声机制详解</AccordionTrigger>
              <AccordionContent>
                <div className="grid md:grid-cols-3 gap-4 pt-4">
                  <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                    <h5 className="font-medium mb-2">Laplace 机制</h5>
                    <p className="text-xs text-muted-foreground">
                      添加 Laplace 噪声：Noise ~ Lap(Δf/ε)<br />
                      适用于数值型查询，提供纯ε-DP 保证
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/5 border border-secondary/20">
                    <h5 className="font-medium mb-2">Gaussian 机制</h5>
                    <p className="text-xs text-muted-foreground">
                      添加高斯噪声：Noise ~ N(0, σ²)<br />
                      适用于高维数据，提供 (ε,δ)-DP 保证
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800">
                    <h5 className="font-medium mb-2">Geometric 机制</h5>
                    <p className="text-xs text-muted-foreground">
                      离散版本的 Laplace 机制<br />
                      适用于计数查询和离散数据
                    </p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
            
            <AccordionItem value="application">
              <AccordionTrigger>应用场景说明</AccordionTrigger>
              <AccordionContent>
                <div className="grid md:grid-cols-3 gap-4 pt-4">
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <h5 className="font-medium mb-2 flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      数据层扰动
                    </h5>
                    <p className="text-xs text-muted-foreground">
                      在原始数据发布前添加噪声，适用于数据共享场景
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <h5 className="font-medium mb-2 flex items-center gap-2">
                      <Sliders className="h-4 w-4" />
                      梯度扰动
                    </h5>
                    <p className="text-xs text-muted-foreground">
                      在深度学习训练过程中对梯度添加噪声，适用于联邦学习
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <h5 className="font-medium mb-2 flex items-center gap-2">
                      <Settings className="h-4 w-4" />
                      模型层扰动
                    </h5>
                    <p className="text-xs text-muted-foreground">
                      对训练完成的模型参数添加噪声，适用于模型发布
                    </p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      {/* Configuration Panel */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Config */}
        <div className="lg:col-span-2 space-y-6">
          {/* Privacy Parameters */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                  <Shield className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>隐私参数配置</CardTitle>
                  <CardDescription>设置差分隐私核心参数</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Epsilon Slider */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Label htmlFor="epsilon" className="text-base flex items-center gap-2">
                    <Key className="h-4 w-4" />
                    隐私预算 ε (Epsilon)
                  </Label>
                  <span className="text-2xl font-bold text-primary">{config.epsilon.toFixed(3)}</span>
                </div>
                <Slider
                  value={config.epsilon}
                  min={0.1}
                  max={10}
                  step={0.1}
                  onChange={(value) => setConfig({ ...config, epsilon: value })}
                  showTooltip={false}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>强保护 (0.1)</span>
                  <span>平衡 (1.0)</span>
                  <span>高效用 (10.0)</span>
                </div>
                <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
                  <div className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-blue-700 dark:text-blue-300">
                      当前 ε = {config.epsilon.toFixed(2)}，属于
                      {config.epsilon < 0.5 ? '强隐私保护级别，数据效用较低' : 
                        config.epsilon < 2 ? '中等隐私保护级别，平衡性较好' : 
                        '弱隐私保护级别，数据效用较高'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Delta Slider */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Label htmlFor="delta" className="text-base flex items-center gap-2">
                    <Lock className="h-4 w-4" />
                    松弛参数 δ (Delta)
                  </Label>
                  <span className="text-2xl font-bold text-primary">{config.delta.toExponential(2)}</span>
                </div>
                <Slider
                  value={config.delta}
                  min={0.000001}
                  max={0.001}
                  step={0.000001}
                  onChange={(value) => setConfig({ ...config, delta: value })}
                  showTooltip={false}
                />
                <p className="text-xs text-muted-foreground">
                  δ 表示隐私保护失败的概率，应远小于 1/数据库大小
                </p>
              </div>

              {/* Sensitivity Slider */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Label htmlFor="sensitivity" className="text-base flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    全局敏感度 Δf
                  </Label>
                  <span className="text-2xl font-bold text-primary">{config.sensitivity.toFixed(2)}</span>
                </div>
                <Slider
                  value={config.sensitivity}
                  min={0.1}
                  max={5}
                  step={0.1}
                  onChange={(value) => setConfig({ ...config, sensitivity: value })}
                  showTooltip={false}
                />
                <p className="text-xs text-muted-foreground">
                  敏感度衡量单个记录变化对查询结果的最大影响
                </p>
              </div>

              {/* Total Budget */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Label htmlFor="privacyBudget" className="text-base flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    总隐私预算 (会话级 ε_total)
                  </Label>
                  <span className="text-2xl font-bold text-primary">{config.privacyBudget.toFixed(1)}</span>
                </div>
                <Slider
                  value={config.privacyBudget}
                  min={0}
                  max={50}
                  step={0.5}
                  onChange={(value) => setConfig({ ...config, privacyBudget: value })}
                  showTooltip={false}
                />
                <div className="p-3 rounded-lg bg-muted/50 border border-border">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Demo 采用「串行组合」的直观记账方式：每次推荐推理消耗约 ε，累计不超过 ε_total。
                    你可以在“用药推荐/可视化”页面看到实时消耗曲线。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Noise Mechanism Selection */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-secondary to-green-600 flex items-center justify-center">
                  <Settings className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>噪声机制选择</CardTitle>
                  <CardDescription>选择适合应用场景的扰动方式</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                {[
                  {
                    id: 'laplace',
                    name: 'Laplace',
                    desc: '数值查询，纯ε-DP',
                    icon: TrendingDown
                  },
                  {
                    id: 'gaussian',
                    name: 'Gaussian',
                    desc: '高维数据，(ε,δ)-DP',
                    icon: Sliders
                  },
                  {
                    id: 'geometric',
                    name: 'Geometric',
                    desc: '离散数据，计数查询',
                    icon: BarChart3
                  },
                ].map((mechanism) => {
                  const Icon = mechanism.icon
                  const isActive = config.noiseMechanism === mechanism.id
                  return (
                    <button
                      key={mechanism.id}
                      onClick={() => setConfig({ ...config, noiseMechanism: mechanism.id as any })}
                      className={`p-4 rounded-xl border-2 transition-all duration-200 text-left ${
                        isActive
                          ? 'border-primary bg-primary/5 shadow-md'
                          : 'border-border hover:border-primary/50 bg-background hover:bg-muted/50'
                      }`}
                    >
                      <Icon className={`h-6 w-6 mb-2 ${isActive ? 'text-primary' : 'text-foreground'}`} />
                      <div className={`font-semibold ${isActive ? 'text-primary' : 'text-foreground'}`}>{mechanism.name}</div>
                      <div className="text-xs text-muted-foreground mt-1">{mechanism.desc}</div>
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Application Stage */}
          <Card className="border-border/40 bg-card/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Eye className="h-5 w-5 text-white" />
                </div>
                <div>
                  <CardTitle>隐私保护应用阶段</CardTitle>
                  <CardDescription>选择噪声注入的位置</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                {[
                  { 
                    id: 'data', 
                    name: '数据层', 
                    desc: '原始数据扰动',
                    color: 'from-blue-500 to-cyan-500'
                  },
                  { 
                    id: 'gradient', 
                    name: '梯度层', 
                    desc: '训练过程扰动',
                    color: 'from-purple-500 to-pink-500'
                  },
                  { 
                    id: 'model', 
                    name: '模型层', 
                    desc: '模型参数扰动',
                    color: 'from-orange-500 to-red-500'
                  },
                ].map((stage) => (
                  <button
                    key={stage.id}
                    onClick={() => setConfig({ ...config, applicationStage: stage.id as any })}
                    className={`p-4 rounded-xl border-2 transition-all duration-200 text-left relative overflow-hidden ${
                      config.applicationStage === stage.id
                        ? 'border-primary bg-primary/5 shadow-md'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className={`absolute top-0 left-0 w-full h-1 bg-gradient-to-r ${stage.color}`} />
                    <div className="font-semibold mt-2">{stage.name}</div>
                    <div className="text-xs text-muted-foreground mt-1">{stage.desc}</div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Real-time Metrics */}
        <div className="space-y-6">
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-lg sticky top-24">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                实时指标分析
              </CardTitle>
              <CardDescription>基于当前配置的评估结果</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Noise Scale */}
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingDown className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">
                    噪声规模 ({config.noiseMechanism === 'gaussian' ? 'σ' : 'b'})
                  </span>
                </div>
                <div className="text-3xl font-bold text-primary mb-1">
                  {noiseScale === Infinity ? '∞' : noiseScale.toFixed(4)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {config.noiseMechanism === 'gaussian'
                    ? 'σ = Δf * sqrt(2 ln(1.25/δ)) / ε（常用近似）'
                    : `b = Δf / ε = ${config.sensitivity} / ${config.epsilon}`}
                </p>
              </div>

              {/* Budget status */}
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-secondary" />
                    <span className="text-sm font-medium">会话隐私预算</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
                    onClick={() => {
                      clearEvents()
                    }}
                  >
                    重置消耗
                  </Button>
                </div>
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <div className="text-xs text-muted-foreground">总预算</div>
                    <div className="text-lg font-semibold">ε_total = {config.privacyBudget.toFixed(1)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">剩余</div>
                    <div className="text-lg font-semibold text-secondary">ε_rem = {budget.remaining.toFixed(2)}</div>
                  </div>
                </div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden mt-3">
                  <div
                    className="h-full bg-gradient-to-r from-secondary to-green-500 transition-all duration-500"
                    style={{
                      width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  已消耗 ε = {budget.spent.toFixed(2)}（建议在 demo 中保持有剩余以体现可持续查询）
                </p>
              </div>

              {/* Privacy Score */}
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-4 w-4 text-secondary" />
                  <span className="text-sm font-medium">隐私保护强度</span>
                </div>
                <div className="flex items-end gap-2 mb-2">
                  <span className="text-3xl font-bold text-secondary">{privacyScore}</span>
                  <span className="text-sm text-muted-foreground mb-1">/ 10</span>
                </div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-secondary to-green-500 transition-all duration-500"
                    style={{ width: `${parseFloat(privacyScore) * 10}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {parseFloat(privacyScore) >= 8 ? '优秀' : parseFloat(privacyScore) >= 6 ? '良好' : '一般'}
                </p>
              </div>

              {/* Utility Loss */}
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-warning" />
                  <span className="text-sm font-medium">预估效用损失</span>
                </div>
                <div className="flex items-end gap-2 mb-2">
                  <span className="text-3xl font-bold text-warning">{utilityLoss}%</span>
                </div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-warning to-orange-500 transition-all duration-500"
                    style={{ width: `${parseFloat(utilityLoss)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  噪声导致的模型性能下降估计
                </p>
              </div>

              {/* Trade-off Visualization */}
              <div className="p-4 rounded-lg bg-background border border-border">
                <div className="text-sm font-medium mb-3">隐私 - 效用权衡</div>
                <div className="relative h-32">
                  {/* Simple trade-off curve visualization */}
                  <svg viewBox="0 0 200 100" className="w-full h-full">
                    {/* Axes */}
                    <line x1="20" y1="80" x2="180" y2="80" stroke="hsl(var(--border))" strokeWidth="2" />
                    <line x1="20" y1="80" x2="20" y2="20" stroke="hsl(var(--border))" strokeWidth="2" />
                    
                    {/* Labels */}
                    <text x="100" y="98" fontSize="10" fill="hsl(var(--muted-foreground))">隐私预算 ε</text>
                    <text x="5" y="50" fontSize="10" fill="hsl(var(--muted-foreground))" transform="rotate(-90, 10, 50)">效用</text>
                    
                    {/* Trade-off curve */}
                    <path
                      d="M 20 30 Q 60 40, 100 55 T 180 75"
                      fill="none"
                      stroke="hsl(var(--primary))"
                      strokeWidth="3"
                    />
                    
                    {/* Current point */}
                    <circle
                      cx={20 + (config.epsilon / 10) * 160}
                      cy={30 + (config.epsilon / 10) * 45}
                      r="6"
                      fill="hsl(var(--secondary))"
                      stroke="white"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>低 ε</span>
                  <span>高 ε</span>
                </div>
              </div>

              {/* Save Button */}
              <Button 
                onClick={handleSave} 
                className="w-full gap-2 shadow-lg"
                size="lg"
              >
                <CheckCircle2 className="h-4 w-4" />
                保存配置
              </Button>

              {savedConfig && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-3 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800"
                >
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-300 text-sm">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>配置已保存！ε={savedConfig.epsilon.toFixed(2)}</span>
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Research Content Display */}
      <Card className="border-border/40 bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle>本课题研究的差分隐私机制</CardTitle>
          <CardDescription>
            针对医疗用药推荐场景的适配性设计
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h4 className="font-semibold flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                研究重点
              </h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
                  <span>医疗数据稀疏性下的隐私预算优化分配策略</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
                  <span>深度学习梯度更新过程中的自适应噪声注入机制</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
                  <span>多阶段差分隐私组合定理的应用与隐私开销累积分析</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
                  <span>药物特征向量化过程中的局部差分隐私保护</span>
                </li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4 text-secondary" />
                技术路线
              </h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" />
                  <span>基于敏感度的自适应噪声缩放算法</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" />
                  <span>联邦学习框架下的分布式差分隐私实现</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" />
                  <span>隐私预算的动态调度与最优分配算法</span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" />
                  <span>模型可解释性与隐私保护的协同优化</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
