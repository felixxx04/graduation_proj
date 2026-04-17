import { Link } from 'react-router-dom'
import {
  Shield,
  Brain,
  Activity,
  Lock,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  Users,
  Stethoscope,
  BarChart3,
  Settings,
  Heart,
  Zap,
  Microscope,
  Database,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/authStore'
import { canAccessFeature } from '@/lib/permissions'

const features = [
  {
    icon: Shield,
    title: '差分隐私保护',
    description: '采用先进的差分隐私技术，为患者医疗数据提供可证明的隐私保障',
    dataColor: 'ia-data-1',
  },
  {
    icon: Brain,
    title: '深度学习推荐',
    description: '基于深度因子分解机模型，精准捕捉药物 - 疾病 - 患者之间的复杂关系',
    dataColor: 'ia-data-2',
  },
  {
    icon: Activity,
    title: '个性化用药',
    description: '综合考虑患者个体差异、疾病特征、药物相互作用，提供定制化建议',
    dataColor: 'ia-data-3',
  },
  {
    icon: Lock,
    title: '安全可控',
    description: '隐私预算可调、噪声机制可选，在隐私保护与推荐性能间实现最佳平衡',
    dataColor: 'ia-data-4',
  },
]

const stats = [
  { label: '隐私保护等级', value: 'ε≤1.0', icon: Lock, dataColor: 'ia-data-1' },
  { label: '推荐准确率', value: '92%+', icon: TrendingUp, dataColor: 'ia-data-3' },
  { label: '支持药物种类', value: '5000+', icon: Database, dataColor: 'ia-data-2' },
  { label: '服务患者数', value: '10000+', icon: Users, dataColor: 'ia-data-5' },
]

const researchGoals = [
  {
    icon: Microscope,
    title: '医疗数据隐私保护',
    items: ['差分隐私机制设计', '隐私预算优化配置', '噪声扰动策略研究'],
  },
  {
    icon: Zap,
    title: '数据稀疏性处理',
    items: ['特征工程优化', '深度表示学习', '多维特征融合'],
  },
  {
    icon: Brain,
    title: '推荐模型构建',
    items: ['深度学习架构', '多因素综合建模', '可解释性增强'],
  },
  {
    icon: Heart,
    title: '隐私与性能平衡',
    items: ['噪声注入方式优化', '模型鲁棒性提升', '性能影响分析'],
  },
]

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-16 pb-8">
      {/* Hero Section — Border-based, editorial layout */}
      <section className="border-l-4 border-l-primary bg-card px-6 py-10 md:px-10 md:py-16">
        <div className="max-w-4xl">
          <div className="ia-badge ia-badge-primary mb-6">
            隐私优先 · 智能推荐
          </div>

          <h1 className="text-ia-hero font-display font-extrabold text-foreground mb-4">
            智医荐药
          </h1>
          <p className="text-ia-section font-display font-medium text-muted-foreground mb-3">
            隐私保护的智能用药推荐系统
          </p>
          <p className="text-ia-body text-muted-foreground max-w-2xl mb-8 leading-relaxed">
            融合差分隐私技术与深度学习算法，在严格保护患者隐私的前提下，
            提供精准、安全、个性化的医疗用药推荐服务
          </p>

          <div className="flex flex-wrap gap-3">
            <Link to="/recommendation">
              <Button size="lg" className="gap-2 cursor-pointer">
                开始用药推荐
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>

            {canAccessFeature(user?.role, 'visualization') && (
              <Link to="/visualization">
                <Button variant="outline" size="lg" className="gap-2 cursor-pointer">
                  <BarChart3 className="h-4 w-4" />
                  效果可视化
                </Button>
              </Link>
            )}

            {canAccessFeature(user?.role, 'admin') && (
              <Link to="/admin">
                <Button variant="outline" size="lg" className="gap-2 cursor-pointer">
                  <Settings className="h-4 w-4" />
                  管理后台
                </Button>
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Stats Section — Data-dense grid */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} hover="border">
              <CardContent className="pt-4 pb-4">
                <div className={`mb-3 flex h-8 w-8 items-center justify-center rounded-standard bg-${stat.dataColor}/10`}>
                  <Icon className={`h-4 w-4 text-${stat.dataColor}`} />
                </div>
                <div className="text-2xl font-heading font-bold text-foreground mb-0.5">
                  {stat.value}
                </div>
                <div className="text-ia-label text-muted-foreground">{stat.label}</div>
              </CardContent>
            </Card>
          )
        })}
      </section>

      {/* Features Section — 2-column editorial */}
      <section className="space-y-8">
        <div className="max-w-2xl">
          <h2 className="text-ia-section font-display font-bold text-foreground mb-3">
            核心功能
          </h2>
          <p className="text-ia-body text-muted-foreground">
            本系统结合医疗用药场景的数据特点与隐私保护需求，打造全方位的智能用药推荐解决方案
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title} hover="border" className="group">
                <CardHeader>
                  <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-standard bg-${feature.dataColor}/10`}>
                    <Icon className={`h-5 w-5 text-${feature.dataColor}`} />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription className="mt-1">
                    {feature.description}
                  </CardDescription>
                </CardHeader>
              </Card>
            )
          })}
        </div>
      </section>

      {/* Research Goals Section — Muted background */}
      <section className="section-light px-6 py-10 md:px-10 -mx-4 md:-mx-8 rounded-comfortable">
        <div className="mb-8">
          <h2 className="text-ia-section font-display font-bold text-foreground mb-3">
            研究目标
          </h2>
          <p className="text-ia-body text-muted-foreground">
            本毕设课题旨在解决医疗用药推荐中的关键问题
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {researchGoals.map((goal) => {
            const Icon = goal.icon
            return (
              <Card key={goal.title} hover="none" className="bg-card">
                <CardHeader>
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-standard bg-primary">
                      <Icon className="h-4 w-4 text-primary-foreground" />
                    </div>
                    <CardTitle className="text-base">{goal.title}</CardTitle>
                  </div>
                  <ul className="space-y-2 pl-1">
                    {goal.items.map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <CheckCircle2 className="h-4 w-4 text-ia-data-3 mt-0.5 flex-shrink-0" />
                        <span className="text-ia-caption text-muted-foreground">{item}</span>
                      </li>
                    ))}
                  </ul>
                </CardHeader>
              </Card>
            )
          })}
        </div>
      </section>

      {/* CTA Section — Dark background */}
      <section className="section-dark px-6 py-12 md:px-10 md:py-16 -mx-4 md:-mx-8 rounded-comfortable text-center">
        <h2 className="text-ia-section font-display font-bold mb-3">
          准备好开始了吗？
        </h2>
        <p className="text-ia-body mb-8 max-w-xl mx-auto" style={{ color: 'hsl(170 10% 60%)' }}>
          体验隐私保护与智能推荐的完美结合，为医疗用药决策提供科学依据
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {canAccessFeature(user?.role, 'patients') && (
            <Link to="/patients">
              <Button size="lg" className="gap-2 cursor-pointer">
                <Users className="h-4 w-4" />
                管理患者档案
              </Button>
            </Link>
          )}
          <Link to="/recommendation">
            <Button variant="outline" size="lg" className="gap-2 cursor-pointer border-white/20 text-white hover:bg-white/10 hover:text-white hover:border-white/40">
              <Stethoscope className="h-4 w-4" />
              获取用药推荐
            </Button>
          </Link>
        </div>
      </section>
    </div>
  )
}
