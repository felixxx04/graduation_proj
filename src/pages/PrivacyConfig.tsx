import { useState } from 'react'
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

  const calculateNoiseScale = () => {
    if (config.noiseMechanism === 'gaussian') return gaussianSigma(config)
    return laplaceScale(config)
  }

  const calculatePrivacyScore = () => {
    const epsilonScore = Math.max(0, 10 - config.epsilon * 5)
    const deltaScore = config.delta < 0.0001 ? 10 : Math.max(0, 10 - config.delta * 10000)
    return ((epsilonScore + deltaScore) / 2).toFixed(1)
  }

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
    <div className="space-y-8">
      {/* Page Header */}
      <section className="border-l-4 border-l-primary bg-card px-6 py-8">
        <div className="flex items-start gap-4">
          <div className="hidden md:flex h-10 w-10 items-center justify-center rounded-standard bg-primary flex-shrink-0">
            <Shield className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="flex-1">
            <h1 className="text-ia-tile font-display font-bold text-foreground mb-2">差分隐私配置</h1>
            <p className="text-ia-body text-muted-foreground max-w-2xl">配置隐私保护参数，在数据安全与模型性能之间寻找最佳平衡点</p>
          </div>
        </div>
      </section>

      {/* Algorithm Explanation */}
      <Card hover="none" className="border-primary/20">
        <CardHeader>
          <div className="flex items-center gap-2.5 mb-1">
            <BookOpen className="h-4 w-4 text-primary" />
            <CardTitle>差分隐私算法原理</CardTitle>
          </div>
          <CardDescription>理解核心概念与数学基础</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-3">
            <div className="p-3 rounded-standard bg-card border border-ia-border">
              <h4 className="font-heading font-semibold text-ia-caption mb-1.5 flex items-center gap-2">
                <Shield className="h-3.5 w-3.5 text-primary" />
                ε-差分隐私定义
              </h4>
              <p className="text-ia-label text-muted-foreground leading-relaxed">
                对于任意两个相邻数据集 D₁ 和 D₂，以及任意输出 S：
                <code className="block mt-1.5 p-1.5 bg-muted rounded-micro text-ia-data overflow-x-auto">
                  Pr[M(D₁) ∈ S] ≤ e^ε × Pr[M(D₂) ∈ S] + δ
                </code>
              </p>
            </div>
            <div className="p-3 rounded-standard bg-card border border-ia-border">
              <h4 className="font-heading font-semibold text-ia-caption mb-1.5 flex items-center gap-2">
                <Lock className="h-3.5 w-3.5 text-secondary" />
                隐私预算 ε
              </h4>
              <p className="text-ia-label text-muted-foreground leading-relaxed">
                ε 越小，隐私保护越强，但数据效用越低。推荐范围：0.1 ~ 10
                <span className="block mt-1">本系统默认 ε = 1.0，提供强隐私保护</span>
              </p>
            </div>
          </div>

          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="mechanism">
              <AccordionTrigger>噪声机制详解</AccordionTrigger>
              <AccordionContent>
                <div className="grid md:grid-cols-3 gap-2 pt-3">
                  <div className="p-2.5 rounded-standard border border-primary/20 bg-primary/4">
                    <h5 className="font-heading font-semibold text-ia-caption mb-1">Laplace 机制</h5>
                    <p className="text-ia-label text-muted-foreground">添加 Laplace 噪声：Noise ~ Lap(Δf/ε)。适用于数值型查询，提供纯ε-DP 保证</p>
                  </div>
                  <div className="p-2.5 rounded-standard border border-secondary/20 bg-secondary/4">
                    <h5 className="font-heading font-semibold text-ia-caption mb-1">Gaussian 机制</h5>
                    <p className="text-ia-label text-muted-foreground">添加高斯噪声：Noise ~ N(0, σ²)。适用于高维数据，提供 (ε,δ)-DP 保证</p>
                  </div>
                  <div className="p-2.5 rounded-standard border border-ia-data-3/20 bg-ia-data-3/4">
                    <h5 className="font-heading font-semibold text-ia-caption mb-1">Geometric 机制</h5>
                    <p className="text-ia-label text-muted-foreground">离散版本的 Laplace 机制。适用于计数查询和离散数据</p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="application">
              <AccordionTrigger>应用场景说明</AccordionTrigger>
              <AccordionContent>
                <div className="grid md:grid-cols-3 gap-2 pt-3">
                  <div className="p-2.5 rounded-standard bg-card border border-ia-border">
                    <h5 className="font-heading font-semibold text-ia-caption mb-1 flex items-center gap-1.5"><Eye className="h-3.5 w-3.5" />数据层扰动</h5>
                    <p className="text-ia-label text-muted-foreground">在原始数据发布前添加噪声，适用于数据共享场景</p>
                  </div>
                  <div className="p-2.5 rounded-standard bg-card border border-ia-border">
                    <h5 className="font-heading font-semibold text-ia-caption mb-1 flex items-center gap-1.5"><Sliders className="h-3.5 w-3.5" />梯度扰动</h5>
                    <p className="text-ia-label text-muted-foreground">在深度学习训练过程中对梯度添加噪声，适用于联邦学习</p>
                  </div>
                  <div className="p-2.5 rounded-standard bg-card border border-ia-border">
                    <h5 className="font-heading font-semibold text-ia-caption mb-1 flex items-center gap-1.5"><Settings className="h-3.5 w-3.5" />模型层扰动</h5>
                    <p className="text-ia-label text-muted-foreground">对训练完成的模型参数添加噪声，适用于模型发布</p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      {/* Configuration Panel */}
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          {/* Privacy Parameters */}
          <Card hover="none">
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-standard bg-primary">
                  <Shield className="h-4 w-4 text-primary-foreground" />
                </div>
                <div>
                  <CardTitle>隐私参数配置</CardTitle>
                  <CardDescription>设置差分隐私核心参数</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label className="text-ia-caption font-heading font-semibold flex items-center gap-2"><Key className="h-3.5 w-3.5" />隐私预算 ε (Epsilon)</Label>
                  <span className="text-xl font-heading font-bold text-primary">{config.epsilon.toFixed(3)}</span>
                </div>
                <Slider value={config.epsilon} min={0.1} max={10} step={0.1} onChange={(value) => setConfig({ ...config, epsilon: value })} showTooltip={false} />
                <div className="flex justify-between text-ia-label text-muted-foreground">
                  <span>强保护 (0.1)</span>
                  <span>平衡 (1.0)</span>
                  <span>高效用 (10.0)</span>
                </div>
                <div className="p-2.5 rounded-standard border border-primary/20 bg-primary/4">
                  <div className="flex items-start gap-2">
                    <Info className="h-3.5 w-3.5 text-primary mt-0.5 flex-shrink-0" />
                    <p className="text-ia-label text-primary/80">
                      当前 ε = {config.epsilon.toFixed(2)}，属于
                      {config.epsilon < 0.5 ? '强隐私保护级别，数据效用较低' : config.epsilon < 2 ? '中等隐私保护级别，平衡性较好' : '弱隐私保护级别，数据效用较高'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label className="text-ia-caption font-heading font-semibold flex items-center gap-2"><Lock className="h-3.5 w-3.5" />松弛参数 δ (Delta)</Label>
                  <span className="text-xl font-heading font-bold text-primary">{config.delta.toExponential(2)}</span>
                </div>
                <Slider value={config.delta} min={0.000001} max={0.001} step={0.000001} onChange={(value) => setConfig({ ...config, delta: value })} showTooltip={false} />
                <p className="text-ia-label text-muted-foreground">δ 表示隐私保护失败的概率，应远小于 1/数据库大小</p>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label className="text-ia-caption font-heading font-semibold flex items-center gap-2"><TrendingDown className="h-3.5 w-3.5" />全局敏感度 Δf</Label>
                  <span className="text-xl font-heading font-bold text-primary">{config.sensitivity.toFixed(2)}</span>
                </div>
                <Slider value={config.sensitivity} min={0.01} max={1.0} step={0.01} onChange={(value) => setConfig({ ...config, sensitivity: value })} showTooltip={false} />
                <p className="text-ia-label text-muted-foreground">敏感度衡量单个记录变化对查询结果的最大影响（sigmoid输出范围[0,1]，上限1.0）</p>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label className="text-ia-caption font-heading font-semibold flex items-center gap-2"><BarChart3 className="h-3.5 w-3.5" />总隐私预算 (会话级 ε_total)</Label>
                  <span className="text-xl font-heading font-bold text-primary">{config.privacyBudget.toFixed(1)}</span>
                </div>
                <Slider value={config.privacyBudget} min={0} max={50} step={0.5} onChange={(value) => setConfig({ ...config, privacyBudget: value })} showTooltip={false} />
                <div className="p-2.5 rounded-standard bg-muted border border-ia-border">
                  <p className="text-ia-label text-muted-foreground">
                    Demo 采用「串行组合」的直观记账方式：每次推荐推理消耗约 ε，累计不超过 ε_total。你可以在"用药推荐/可视化"页面看到实时消耗曲线。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Noise Mechanism Selection */}
          <Card hover="none">
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-standard bg-secondary">
                  <Settings className="h-4 w-4 text-secondary-foreground" />
                </div>
                <div>
                  <CardTitle>噪声机制选择</CardTitle>
                  <CardDescription>选择适合应用场景的扰动方式</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-3">
                {[
                  { id: 'laplace', name: 'Laplace', desc: '数值查询，纯ε-DP', icon: TrendingDown },
                  { id: 'gaussian', name: 'Gaussian', desc: '高维数据，(ε,δ)-DP', icon: Sliders },
                  { id: 'geometric', name: 'Geometric', desc: '离散数据，计数查询', icon: BarChart3 },
                ].map((mechanism) => {
                  const Icon = mechanism.icon
                  const isActive = config.noiseMechanism === mechanism.id
                  return (
                    <button
                      key={mechanism.id}
                      onClick={() => setConfig({ ...config, noiseMechanism: mechanism.id as any })}
                      className={`p-3 rounded-standard border transition-colors duration-150 text-left cursor-pointer ${
                        isActive ? 'border-primary bg-primary/4 ia-border-3' : 'border-ia-border hover:border-primary/40'
                      }`}
                    >
                      <Icon className={`h-5 w-5 mb-1.5 ${isActive ? 'text-primary' : 'text-foreground'}`} />
                      <div className={`font-heading font-semibold text-ia-caption ${isActive ? 'text-primary' : 'text-foreground'}`}>{mechanism.name}</div>
                      <div className="text-ia-label text-muted-foreground mt-0.5">{mechanism.desc}</div>
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Application Stage */}
          <Card hover="none">
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-standard bg-ia-data-2">
                  <Eye className="h-4 w-4 text-white" />
                </div>
                <div>
                  <CardTitle>隐私保护应用阶段</CardTitle>
                  <CardDescription>选择噪声注入的位置</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-3">
                {[
                  { id: 'data', name: '数据层', desc: '原始数据扰动' },
                  { id: 'gradient', name: '梯度层', desc: '训练过程扰动' },
                  { id: 'model', name: '模型层', desc: '模型参数扰动' },
                ].map((stage) => (
                  <button
                    key={stage.id}
                    onClick={() => setConfig({ ...config, applicationStage: stage.id as any })}
                    className={`p-3 rounded-standard border transition-colors duration-150 text-left cursor-pointer ${
                      config.applicationStage === stage.id ? 'border-primary bg-primary/4 ia-border-3' : 'border-ia-border hover:border-primary/40'
                    }`}
                  >
                    <div className="font-heading font-semibold text-ia-caption">{stage.name}</div>
                    <div className="text-ia-label text-muted-foreground mt-0.5">{stage.desc}</div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Real-time Metrics */}
        <div className="space-y-5">
          <Card hover="none" className="sticky top-20 border-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-primary" />
                实时指标分析
              </CardTitle>
              <CardDescription>基于当前配置的评估结果</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 rounded-standard bg-card border border-ia-border">
                <div className="flex items-center gap-2 mb-1.5">
                  <TrendingDown className="h-3.5 w-3.5 text-primary" />
                  <span className="text-ia-caption font-heading font-semibold">噪声规模 ({config.noiseMechanism === 'gaussian' ? 'σ' : 'b'})</span>
                </div>
                <div className="text-2xl font-heading font-bold text-primary mb-0.5">{noiseScale === Infinity ? '∞' : noiseScale.toFixed(4)}</div>
                <p className="text-ia-label text-muted-foreground">
                  {config.noiseMechanism === 'gaussian' ? 'σ = Δf * sqrt(2 ln(1.25/δ)) / ε' : `b = Δf / ε = ${config.sensitivity} / ${config.epsilon}`}
                </p>
              </div>

              <div className="p-3 rounded-standard bg-card border border-ia-border">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <Key className="h-3.5 w-3.5 text-secondary" />
                    <span className="text-ia-caption font-heading font-semibold">会话隐私预算</span>
                  </div>
                  <Button variant="outline" size="sm" className="h-7 text-ia-label cursor-pointer" onClick={() => { clearEvents() }}>重置消耗</Button>
                </div>
                <div className="flex items-end justify-between gap-2">
                  <div>
                    <div className="text-ia-label text-muted-foreground">总预算</div>
                    <div className="font-heading font-semibold text-ia-body">ε_total = {config.privacyBudget.toFixed(1)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-ia-label text-muted-foreground">剩余</div>
                    <div className="font-heading font-semibold text-ia-body text-secondary">ε_rem = {budget.remaining.toFixed(2)}</div>
                  </div>
                </div>
                <div className="progress-bar mt-2">
                  <div className="progress-bar-fill" style={{ width: `${config.privacyBudget <= 0 ? 0 : Math.min(100, (budget.spent / config.privacyBudget) * 100)}%` }} />
                </div>
                <p className="text-ia-label text-muted-foreground mt-1.5">
                  已消耗 ε = {budget.spent.toFixed(2)}
                </p>
              </div>

              <div className="p-3 rounded-standard bg-card border border-ia-border">
                <div className="flex items-center gap-2 mb-1.5">
                  <Shield className="h-3.5 w-3.5 text-secondary" />
                  <span className="text-ia-caption font-heading font-semibold">隐私保护强度</span>
                </div>
                <div className="flex items-end gap-1.5 mb-1.5">
                  <span className="text-2xl font-heading font-bold text-secondary">{privacyScore}</span>
                  <span className="text-ia-caption text-muted-foreground mb-0.5">/ 10</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill progress-bar-fill-success" style={{ width: `${parseFloat(privacyScore) * 10}%` }} />
                </div>
                <p className="text-ia-label text-muted-foreground mt-1.5">
                  {parseFloat(privacyScore) >= 8 ? '优秀' : parseFloat(privacyScore) >= 6 ? '良好' : '一般'}
                </p>
              </div>

              <div className="p-3 rounded-standard bg-card border border-ia-border">
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-ia-data-4" />
                  <span className="text-ia-caption font-heading font-semibold">预估效用损失</span>
                </div>
                <div className="flex items-end gap-1.5 mb-1.5">
                  <span className="text-2xl font-heading font-bold text-ia-data-4">{utilityLoss}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-bar-fill progress-bar-fill-warning" style={{ width: `${parseFloat(utilityLoss)}%` }} />
                </div>
                <p className="text-ia-label text-muted-foreground mt-1.5">噪声导致的模型性能下降估计</p>
              </div>

              {/* Trade-off Visualization */}
              <div className="p-3 rounded-standard bg-card border border-ia-border">
                <div className="text-ia-caption font-heading font-semibold mb-2">隐私 - 效用权衡</div>
                <div className="relative h-28">
                  <svg viewBox="0 0 200 100" className="w-full h-full">
                    <line x1="20" y1="80" x2="180" y2="80" stroke="hsl(var(--border))" strokeWidth="1.5" />
                    <line x1="20" y1="80" x2="20" y2="20" stroke="hsl(var(--border))" strokeWidth="1.5" />
                    <text x="100" y="98" fontSize="9" fill="hsl(var(--muted-foreground))">隐私预算 ε</text>
                    <text x="5" y="50" fontSize="9" fill="hsl(var(--muted-foreground))" transform="rotate(-90, 10, 50)">效用</text>
                    <path d="M 20 30 Q 60 40, 100 55 T 180 75" fill="none" stroke="hsl(var(--primary))" strokeWidth="2" />
                    <circle cx={20 + (config.epsilon / 10) * 160} cy={30 + (config.epsilon / 10) * 45} r="5" fill="hsl(var(--secondary))" stroke="white" strokeWidth="1.5" />
                  </svg>
                </div>
                <div className="flex justify-between text-ia-label text-muted-foreground mt-1">
                  <span>低 ε</span>
                  <span>高 ε</span>
                </div>
              </div>

              <Button onClick={handleSave} className="w-full gap-2 cursor-pointer" size="lg">
                <CheckCircle2 className="h-4 w-4" />
                保存配置
              </Button>

              {savedConfig && (
                <div className="p-2.5 rounded-standard border border-ia-data-3/30 bg-ia-data-3/6">
                  <div className="flex items-center gap-2 text-ia-data-3 text-ia-caption">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span className="font-heading font-semibold">配置已保存！ε={savedConfig.epsilon.toFixed(2)}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Research Content */}
      <Card hover="none">
        <CardHeader>
          <CardTitle>本课题研究的差分隐私机制</CardTitle>
          <CardDescription>针对医疗用药推荐场景的适配性设计</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-5">
            <div className="space-y-2.5">
              <h4 className="font-heading font-semibold text-ia-caption flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                研究重点
              </h4>
              <ul className="space-y-1.5 text-ia-caption text-muted-foreground">
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" /><span>医疗数据稀疏性下的隐私预算优化分配策略</span></li>
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" /><span>深度学习梯度更新过程中的自适应噪声注入机制</span></li>
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" /><span>多阶段差分隐私组合定理的应用与隐私开销累积分析</span></li>
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" /><span>药物特征向量化过程中的局部差分隐私保护</span></li>
              </ul>
            </div>
            <div className="space-y-2.5">
              <h4 className="font-heading font-semibold text-ia-caption flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-secondary" />
                技术路线
              </h4>
              <ul className="space-y-1.5 text-ia-caption text-muted-foreground">
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" /><span>基于敏感度的自适应噪声缩放算法</span></li>
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" /><span>联邦学习框架下的分布式差分隐私实现</span></li>
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" /><span>隐私预算的动态调度与最优分配算法</span></li>
                <li className="flex items-start gap-2"><div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5" /><span>模型可解释性与隐私保护的协同优化</span></li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
