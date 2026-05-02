import { Link } from 'react-router-dom'
import {
  Shield, Brain, Activity, Lock, ArrowRight,
  TrendingUp, Users, Stethoscope, BarChart3, Settings, Database,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/authStore'
import { canAccessFeature } from '@/lib/permissions'

const features = [
  { icon: Shield, title: '差分隐私保护', description: '采用先进的差分隐私技术，为患者医疗数据提供可证明的隐私保障', color: 'sky' as const },
  { icon: Brain, title: '深度学习推荐', description: '基于深度因子分解机模型，精准捕捉药物-疾病-患者之间的复杂关系', color: 'teal' as const },
  { icon: Activity, title: '个性化用药', description: '综合考虑患者个体差异、疾病特征、药物相互作用，提供定制化建议', color: 'sky' as const },
  { icon: Lock, title: '安全可控', description: '隐私预算可调、噪声机制可选，在隐私保护与推荐性能间实现最佳平衡', color: 'teal' as const },
]

const stats = [
  { label: '隐私保护等级', value: 'ε ≤ 1.0', icon: Shield, valueColor: 'text-brand-sky' },
  { label: '推荐准确率', value: '92%+', icon: TrendingUp, valueColor: 'text-brand-teal' },
  { label: '药物种类', value: '5,000+', icon: Database, valueColor: 'text-brand-sky' },
  { label: '服务患者', value: '10,000+', icon: Users, valueColor: 'text-brand-teal' },
]

const iconBgMap: Record<string, string> = {
  sky: 'bg-brand-sky/10',
  teal: 'bg-brand-teal/10',
}

const iconColorMap: Record<string, string> = {
  sky: 'text-brand-sky',
  teal: 'text-brand-teal',
}

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-20 pb-12">
      {/* Hero Section — Asymmetric split layout */}
      <section className="relative overflow-hidden rounded-xl bg-gradient-to-br from-background via-surface to-surface-elevated border border-white/[0.06]">
        {/* Geometric decorations */}
        <div className="hero-circle hero-circle-lg" style={{ top: -80, right: -40, width: 320, height: 320 }} />
        <div className="hero-circle hero-circle-md" style={{ bottom: -40, right: 120, width: 180, height: 180 }} />
        <div className="hero-dot" style={{ top: 60, right: 200, width: 8, height: 8 }} />
        <div className="hero-dot" style={{ bottom: 100, right: 80, width: 6, height: 6 }} />

        <div className="relative z-10 grid lg:grid-cols-2 gap-8 p-8 md:p-12 lg:p-16">
          {/* Left content */}
          <div className="flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-brand-sky/20 bg-brand-sky/8 text-xs text-brand-sky font-medium mb-6 w-fit">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-sky animate-brand-pulse" />
              AI-Powered Clinical Decision Support
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-[3rem] font-extrabold text-foreground mb-4 leading-[1.1] tracking-[-0.03em]">
              精准用药推荐<br />
              <span className="gradient-text">守护患者隐私</span>
            </h1>

            <p className="text-base text-muted-foreground max-w-lg mb-8 leading-relaxed">
              融合差分隐私技术与深度学习算法，在严格保护患者隐私的前提下，
              提供精准、安全、个性化的医疗用药推荐服务
            </p>

            <div className="flex flex-wrap gap-3">
              <Link to="/recommendation">
                <Button size="lg" className="gap-2">
                  开始用药推荐
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              {canAccessFeature(user?.role, 'visualization') && (
                <Link to="/visualization">
                  <Button variant="outline" size="lg" className="gap-2">
                    <BarChart3 className="h-4 w-4" />
                    效果可视化
                  </Button>
                </Link>
              )}
              {canAccessFeature(user?.role, 'admin') && (
                <Link to="/admin">
                  <Button variant="outline" size="lg" className="gap-2">
                    <Settings className="h-4 w-4" />
                    管理后台
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Right — Privacy budget visual */}
          <div className="flex items-center justify-center">
            <div className="w-52 h-64 rounded-xl border border-white/[0.08] bg-surface-elevated/50 flex flex-col items-center justify-center gap-3 shadow-sm">
              <div className="text-5xl font-extrabold text-brand-sky">ε</div>
              <div className="text-[10px] text-brand-teal tracking-[0.12em] uppercase font-semibold">Differential Privacy</div>
              <div className="w-20 h-px bg-gradient-to-r from-transparent via-brand-sky/30 to-transparent" />
              <div className="text-3xl font-bold text-foreground">≤ 1.0</div>
              <div className="text-xs text-muted-foreground">PRIVACY BUDGET</div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Row */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="group">
              <CardContent className="pt-5 pb-5">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-sm bg-surface">
                  <Icon className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
                </div>
                <div className={`text-2xl font-bold mb-0.5 ${stat.valueColor}`}>{stat.value}</div>
                <div className="text-xs text-muted-foreground font-medium">{stat.label}</div>
              </CardContent>
            </Card>
          )
        })}
      </section>

      {/* Features Grid */}
      <section className="space-y-8">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-bold text-foreground mb-3">核心功能</h2>
          <p className="text-base text-muted-foreground">
            本系统结合医疗用药场景的数据特点与隐私保护需求，打造全方位的智能用药推荐解决方案
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title} className="group">
                <CardHeader>
                  <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-sm ${iconBgMap[feature.color]}`}>
                    <Icon className={`h-5 w-5 ${iconColorMap[feature.color]}`} />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription className="mt-1">{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            )
          })}
        </div>
      </section>

      {/* CTA Section */}
      <section className="rounded-xl bg-gradient-to-br from-surface-overlay to-surface-elevated border border-white/[0.06] px-8 py-14 md:px-14 md:py-16 text-center">
        <h2 className="text-2xl font-bold text-foreground mb-3">准备好开始了吗？</h2>
        <p className="text-base text-muted-foreground mb-8 max-w-lg mx-auto">
          体验隐私保护与智能推荐的完美结合，为医疗用药决策提供科学依据
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {canAccessFeature(user?.role, 'patients') && (
            <Link to="/patients">
              <Button size="lg" className="gap-2">
                <Users className="h-4 w-4" />
                管理患者档案
              </Button>
            </Link>
          )}
          <Link to="/recommendation">
            <Button variant="outline" size="lg" className="gap-2">
              <Stethoscope className="h-4 w-4" />
              获取用药推荐
            </Button>
          </Link>
        </div>
      </section>
    </div>
  )
}
