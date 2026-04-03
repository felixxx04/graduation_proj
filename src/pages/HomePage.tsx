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
  Settings,
  Heart,
  Zap,
  Microscope,
  Database
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
    gradient: 'from-blue-500 via-cyan-500 to-teal-500',
    bgPattern: 'medical-dna',
  },
  {
    icon: Brain,
    title: '深度学习推荐',
    description: '基于深度因子分解机模型，精准捕捉药物 - 疾病 - 患者之间的复杂关系',
    gradient: 'from-purple-500 via-fuchsia-500 to-pink-500',
    bgPattern: 'ecg-line',
  },
  {
    icon: Activity,
    title: '个性化用药',
    description: '综合考虑患者个体差异、疾病特征、药物相互作用，提供定制化建议',
    gradient: 'from-orange-500 via-amber-500 to-yellow-500',
    bgPattern: 'medical-dna',
  },
  {
    icon: Lock,
    title: '安全可控',
    description: '隐私预算可调、噪声机制可选，在隐私保护与推荐性能间实现最佳平衡',
    gradient: 'from-emerald-500 via-green-500 to-teal-500',
    bgPattern: 'ecg-line',
  },
]

const stats = [
  { label: '隐私保护等级', value: 'ε≤1.0', icon: Lock, color: 'text-blue-500' },
  { label: '推荐准确率', value: '92%+', icon: TrendingUp, color: 'text-emerald-500' },
  { label: '支持药物种类', value: '5000+', icon: Database, color: 'text-purple-500' },
  { label: '服务患者数', value: '10000+', icon: Users, color: 'text-orange-500' },
]

const researchGoals = [
  {
    icon: Microscope,
    title: '医疗数据隐私保护',
    items: ['差分隐私机制设计', '隐私预算优化配置', '噪声扰动策略研究'],
    gradient: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Zap,
    title: '数据稀疏性处理',
    items: ['特征工程优化', '深度表示学习', '多维特征融合'],
    gradient: 'from-purple-500 to-pink-500',
  },
  {
    icon: Brain,
    title: '推荐模型构建',
    items: ['深度学习架构', '多因素综合建模', '可解释性增强'],
    gradient: 'from-orange-500 to-amber-500',
  },
  {
    icon: Heart,
    title: '隐私与性能平衡',
    items: ['噪声注入方式优化', '模型鲁棒性提升', '性能影响分析'],
    gradient: 'from-emerald-500 to-teal-500',
  },
]

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-20 pb-8">
      {/* Hero Section - Redesigned */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
        className="relative overflow-hidden"
      >
        {/* Background with medical pattern */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 rounded-3xl" />
        <div className="absolute inset-0 bg-medical-dna opacity-30" />

        {/* Decorative circles */}
        <div className="absolute -top-20 -right-20 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />
        <div className="absolute -bottom-20 -left-20 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-teal-500/10 rounded-full blur-3xl" />

        <div className="relative z-10 px-8 py-16 md:px-16 md:py-24">
          <div className="max-w-5xl mx-auto">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="inline-flex items-center gap-3 px-5 py-2.5 rounded-full bg-white/10 backdrop-blur-md border border-white/20 mb-8"
            >
              <div className="relative">
                <Shield className="h-5 w-5 text-cyan-400" />
                <div className="absolute inset-0 animate-ping">
                  <Shield className="h-5 w-5 text-cyan-400/50" />
                </div>
              </div>
              <span className="text-sm font-medium text-white/90 tracking-wide">隐私优先 · 智能推荐</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </motion.div>

            {/* Title */}
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6 }}
              className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight tracking-tight"
            >
              <span className="block bg-gradient-to-r from-white via-blue-100 to-cyan-200 bg-clip-text text-transparent">
                智医荐药
              </span>
              <span className="block text-2xl md:text-3xl lg:text-4xl font-medium text-white/70 mt-2">
                隐私保护的智能用药推荐系统
              </span>
            </motion.h1>

            {/* Description */}
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="text-lg md:text-xl text-white/60 mb-10 max-w-2xl leading-relaxed font-light"
            >
              融合差分隐私技术与深度学习算法，在严格保护患者隐私的前提下，
              提供精准、安全、个性化的医疗用药推荐服务
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6 }}
              className="flex flex-wrap gap-4"
            >
              <Link to="/recommendation">
                <Button
                  size="lg"
                  className="group relative overflow-hidden bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white border-0 px-8 py-6 text-lg font-semibold shadow-lg shadow-blue-500/25 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/30 hover:-translate-y-0.5"
                >
                  <span className="relative z-10 flex items-center gap-2">
                    开始用药推荐
                    <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                  </span>
                </Button>
              </Link>

              {canAccessFeature(user?.role, 'visualization') ? (
                <Link to="/visualization">
                  <Button
                    size="lg"
                    variant="outline"
                    className="px-8 py-6 text-lg font-medium border-white/20 text-white bg-white/5 hover:bg-white/10 backdrop-blur-sm transition-all duration-300 hover:-translate-y-0.5"
                  >
                    <BarChart3 className="h-5 w-5 mr-2" />
                    效果可视化
                  </Button>
                </Link>
              ) : null}

              {canAccessFeature(user?.role, 'admin') && (
                <Link to="/admin">
                  <Button
                    size="lg"
                    variant="outline"
                    className="px-8 py-6 text-lg font-medium border-white/20 text-white bg-white/5 hover:bg-white/10 backdrop-blur-sm transition-all duration-300 hover:-translate-y-0.5"
                  >
                    <Settings className="h-5 w-5 mr-2" />
                    管理后台
                  </Button>
                </Link>
              )}
            </motion.div>
          </div>
        </div>

        {/* Bottom gradient fade */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
      </motion.section>

      {/* Stats Section - Floating Cards */}
      <motion.section
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.6 }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-4 -mt-8 relative z-20"
      >
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 + index * 0.1, duration: 0.5 }}
            >
              <Card className="group relative overflow-hidden border-0 shadow-lg hover:shadow-xl transition-all duration-300 bg-white dark:bg-slate-900 card-hover-lift">
                <CardContent className="pt-6 pb-5 px-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className={`p-2.5 rounded-xl bg-gradient-to-br from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-700`}>
                      <Icon className={`h-5 w-5 ${stat.color}`} />
                    </div>
                  </div>
                  <div className="text-3xl font-bold text-gradient-primary mb-1">
                    {stat.value}
                  </div>
                  <div className="text-sm text-muted-foreground font-medium">{stat.label}</div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </motion.section>

      {/* Features Section - Enhanced */}
      <section className="space-y-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-3xl mx-auto"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-gradient-primary">
            核心功能
          </h2>
          <p className="text-muted-foreground text-lg">
            本系统结合医疗用药场景的数据特点与隐私保护需求，打造全方位的智能用药推荐解决方案
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
              >
                <Card className="group h-full border-0 shadow-md hover:shadow-xl transition-all duration-500 overflow-hidden bg-white dark:bg-slate-900 card-hover-lift">
                  <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${feature.gradient}`} />
                  <CardHeader className="pb-4">
                    <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-5 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                      <Icon className="h-8 w-8 text-white" />
                    </div>
                    <CardTitle className="text-xl font-bold">{feature.title}</CardTitle>
                    <CardDescription className="text-base leading-relaxed mt-2">
                      {feature.description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </section>

      {/* Research Goals Section - Redesigned */}
      <section className="relative">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-slate-900 dark:via-blue-950 dark:to-indigo-950 rounded-3xl" />
        <div className="absolute inset-0 bg-medical-dna opacity-40 rounded-3xl" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative z-10 px-8 py-16 md:px-12"
        >
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 text-gradient-primary">
              研究目标
            </h2>
            <p className="text-muted-foreground text-lg">
              本毕设课题旨在解决医疗用药推荐中的关键问题
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {researchGoals.map((goal, index) => {
              const Icon = goal.icon
              return (
                <motion.div
                  key={goal.title}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1, duration: 0.5 }}
                >
                  <Card className="h-full border-0 shadow-md bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm overflow-hidden group">
                    <div className={`absolute top-0 left-0 w-1 h-full bg-gradient-to-b ${goal.gradient}`} />
                    <CardHeader className="pl-8">
                      <div className="flex items-center gap-3 mb-4">
                        <div className={`p-2.5 rounded-xl bg-gradient-to-br ${goal.gradient} shadow-md`}>
                          <Icon className="h-5 w-5 text-white" />
                        </div>
                        <CardTitle className="text-lg font-bold">{goal.title}</CardTitle>
                      </div>
                      <ul className="space-y-3">
                        {goal.items.map((item, i) => (
                          <motion.li
                            key={item}
                            initial={{ opacity: 0, x: -10 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.3 + i * 0.1, duration: 0.4 }}
                            className="flex items-start gap-3"
                          >
                            <CheckCircle2 className="h-5 w-5 text-emerald-500 mt-0.5 flex-shrink-0" />
                            <span className="text-muted-foreground">{item}</span>
                          </motion.li>
                        ))}
                      </ul>
                    </CardHeader>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      </section>

      {/* CTA Section - Enhanced */}
      <motion.section
        initial={{ opacity: 0, scale: 0.98 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden rounded-3xl"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600" />
        <div className="absolute inset-0 bg-medical-dna opacity-20" />

        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />

        <div className="relative z-10 px-8 py-16 md:px-16 md:py-20 text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-3xl md:text-4xl font-bold text-white mb-4"
          >
            准备好开始了吗？
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="text-white/80 mb-10 max-w-2xl mx-auto text-lg"
          >
            体验隐私保护与智能推荐的完美结合，为医疗用药决策提供科学依据
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="flex flex-wrap justify-center gap-4"
          >
            {canAccessFeature(user?.role, 'patients') && (
              <Link to="/patients">
                <Button
                  size="lg"
                  className="px-8 py-6 text-lg font-bold bg-slate-900 text-white hover:bg-slate-800 shadow-xl transition-all duration-300 hover:-translate-y-0.5 border-0"
                >
                  <Users className="h-5 w-5 mr-2" />
                  管理患者档案
                </Button>
              </Link>
            )}
            <Link to="/recommendation">
              <Button
                size="lg"
                className="px-8 py-6 text-lg font-bold border-2 border-white text-white bg-white/10 hover:bg-white/20 backdrop-blur-sm transition-all duration-300 hover:-translate-y-0.5"
              >
                <Stethoscope className="h-5 w-5 mr-2" />
                获取用药推荐
              </Button>
            </Link>
          </motion.div>
        </div>
      </motion.section>
    </div>
  )
}
