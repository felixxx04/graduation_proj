import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
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
  Settings
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
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Brain,
    title: '深度学习推荐',
    description: '基于深度因子分解机模型，精准捕捉药物 - 疾病 - 患者之间的复杂关系',
    color: 'from-purple-500 to-pink-500',
  },
  {
    icon: Activity,
    title: '个性化用药',
    description: '综合考虑患者个体差异、疾病特征、药物相互作用，提供定制化建议',
    color: 'from-orange-500 to-red-500',
  },
  {
    icon: Lock,
    title: '安全可控',
    description: '隐私预算可调、噪声机制可选，在隐私保护与推荐性能间实现最佳平衡',
    color: 'from-green-500 to-emerald-500',
  },
]

const stats = [
  { label: '隐私保护等级', value: 'ε≤1.0', icon: Lock },
  { label: '推荐准确率', value: '92%+', icon: TrendingUp },
  { label: '支持药物种类', value: '5000+', icon: Activity },
  { label: '服务患者数', value: '10000+', icon: Users },
]

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <motion.section 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary via-primary/80 to-secondary p-8 md:p-16 text-white shadow-2xl"
      >
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-grid-white/10 [mask-image:linear-gradient(0deg,transparent,black)]" />
        
        <div className="relative z-10 max-w-4xl">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 mb-6"
          >
            <Shield className="h-4 w-4" />
            <span className="text-sm font-medium">隐私优先 · 智能推荐</span>
          </motion.div>
          
          <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
            智医荐药
            <br />
            <span className="text-white/90">隐私保护的智能用药推荐系统</span>
          </h1>
          
          <p className="text-lg md:text-xl text-white/80 mb-8 max-w-2xl leading-relaxed">
            融合差分隐私技术与深度学习算法，在严格保护患者隐私的前提下，
            提供精准、安全、个性化的医疗用药推荐服务
          </p>
          
          <div className="flex flex-wrap gap-4">
            <Link to="/recommendation">
              <Button size="lg" variant="secondary" className="gap-2">
                开始用药推荐
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>

            {canAccessFeature(user?.role, 'visualization') ? (
              <Link to="/visualization">
                <Button size="lg" className="bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20 gap-2">
                  <BarChart3 className="h-4 w-4" />
                  效果可视化
                </Button>
              </Link>
            ) : (
              <Link to="/recommendation">
                <Button size="lg" className="bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20">
                  了解系统能力
                </Button>
              </Link>
            )}

            {canAccessFeature(user?.role, 'admin') && (
              <Link to="/admin">
                <Button size="lg" className="bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20 gap-2">
                  <Settings className="h-4 w-4" />
                  管理后台
                </Button>
              </Link>
            )}
          </div>
        </div>
      </motion.section>

      {/* Stats Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="text-center border-border/40 bg-card/50 backdrop-blur hover:shadow-lg transition-all duration-300">
              <CardContent className="pt-6">
                <Icon className="h-8 w-8 mx-auto mb-3 text-primary" />
                <div className="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </CardContent>
            </Card>
          )
        })}
      </motion.section>

      {/* Features Section */}
      <section>
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            核心功能
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            本系统结合医疗用药场景的数据特点与隐私保护需求，打造全方位的智能用药推荐解决方案
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index, duration: 0.5 }}
              >
                <Card className="h-full border-border/40 bg-card/50 backdrop-blur hover:shadow-xl transition-all duration-300 group">
                  <CardHeader>
                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                      <Icon className="h-7 w-7 text-white" />
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                    <CardDescription className="text-base leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </section>

      {/* Research Goals Section */}
      <section className="bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-blue-950 rounded-3xl p-8 md:p-12 border border-border/40">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold mb-4 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            研究目标
          </h2>
          <p className="text-muted-foreground">
            本毕设课题旨在解决医疗用药推荐中的关键问题
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          {[
            {
              title: '医疗数据隐私保护',
              items: ['差分隐私机制设计', '隐私预算优化配置', '噪声扰动策略研究'],
            },
            {
              title: '数据稀疏性处理',
              items: ['特征工程优化', '深度表示学习', '多维特征融合'],
            },
            {
              title: '推荐模型构建',
              items: ['深度学习架构', '多因素综合建模', '可解释性增强'],
            },
            {
              title: '隐私与性能平衡',
              items: ['噪声注入方式优化', '模型鲁棒性提升', '性能影响分析'],
            },
          ].map((goal) => (
            <Card key={goal.title} className="border-border/40 bg-card/80 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg mb-4">{goal.title}</CardTitle>
                <ul className="space-y-3">
                  {goal.items.map((item) => (
                    <li key={item} className="flex items-start gap-3">
                      <CheckCircle2 className="h-5 w-5 text-secondary mt-0.5 flex-shrink-0" />
                      <span className="text-muted-foreground">{item}</span>
                    </li>
                  ))}
                </ul>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <motion.section
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary to-secondary p-8 md:p-12 text-center text-white shadow-2xl"
      >
        <div className="relative z-10">
          <h2 className="text-3xl font-bold mb-4">准备好开始了吗？</h2>
          <p className="text-white/90 mb-8 max-w-2xl mx-auto">
            体验隐私保护与智能推荐的完美结合，为医疗用药决策提供科学依据
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            {canAccessFeature(user?.role, 'patients') && (
              <Link to="/patients">
                <Button size="lg" variant="secondary" className="gap-2">
                  <Users className="h-4 w-4" />
                  管理患者档案
                </Button>
              </Link>
            )}
            <Link to="/recommendation">
              <Button size="lg" className="bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20">
                <Stethoscope className="h-4 w-4 mr-2" />
                获取用药推荐
              </Button>
            </Link>
          </div>
        </div>
      </motion.section>
    </div>
  )
}
