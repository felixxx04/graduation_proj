import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Lock, KeyRound, LogIn, Heart, Activity, Pill, Stethoscope, Sparkles, ArrowLeft } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/lib/authStore'

export default function LoginPage() {
  const { login, isAuthenticated, isInitializing } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const from = useMemo(() => {
    const target = location.state?.from
    return typeof target === 'string' && target.length > 0 ? target : '/'
  }, [location.state?.from])

  useEffect(() => {
    if (!isInitializing && isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [from, isAuthenticated, isInitializing, navigate])

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    const result = await login({ username, password })
    setLoading(false)

    if (!result.ok) {
      setError(result.message)
      return
    }

    navigate(from, { replace: true })
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      {/* Animated Background */}
      <div className="absolute inset-0 -z-10">
        {/* Base Gradient */}
        <div className="absolute inset-0 bg-mesh-gradient" />

        {/* Floating Medical Icons */}
        <div className="absolute inset-0 overflow-hidden">
          {[
            { Icon: Heart, delay: 0, x: '8%', y: '15%', size: 28, opacity: 0.12 },
            { Icon: Activity, delay: 1, x: '88%', y: '12%', size: 36, opacity: 0.1 },
            { Icon: Pill, delay: 2, x: '78%', y: '72%', size: 32, opacity: 0.08 },
            { Icon: Stethoscope, delay: 1.5, x: '12%', y: '78%', size: 34, opacity: 0.1 },
            { Icon: Shield, delay: 0.5, x: '92%', y: '42%', size: 30, opacity: 0.09 },
            { Icon: Heart, delay: 2.5, x: '22%', y: '45%', size: 22, opacity: 0.08 },
            { Icon: Activity, delay: 3, x: '65%', y: '88%', size: 26, opacity: 0.1 },
            { Icon: Pill, delay: 1.8, x: '42%', y: '8%', size: 20, opacity: 0.07 },
          ].map((item, index) => (
            <motion.div
              key={index}
              className="absolute text-primary"
              style={{
                left: item.x,
                top: item.y,
              }}
              initial={{ opacity: 0, scale: 0.5, rotate: -20 }}
              animate={{
                opacity: item.opacity,
                scale: 1,
                rotate: 0,
                y: [0, -15, 0],
              }}
              transition={{
                delay: item.delay * 0.3,
                duration: 4,
                repeat: Infinity,
                repeatType: 'loop',
                ease: 'easeInOut',
              }}
            >
              <item.Icon size={item.size} />
            </motion.div>
          ))}
        </div>

        {/* Gradient Orbs */}
        <div className="absolute -left-32 -top-32 h-80 w-80 rounded-full bg-gradient-to-br from-primary/25 to-accent/15 blur-3xl" />
        <div className="absolute -right-32 -bottom-32 h-96 w-96 rounded-full bg-gradient-to-br from-secondary/20 to-teal-500/10 blur-3xl" />
        <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-accent/10 to-primary/10 blur-3xl" />
      </div>

      {/* Login Card */}
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="relative w-full max-w-md"
      >
        {/* Glow Effect */}
        <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-primary/30 via-accent/30 to-secondary/30 blur-xl opacity-50" />

        <Card className="relative border-primary/20 bg-card/90 backdrop-blur-xl shadow-2xl">
          <CardHeader className="space-y-4 pb-6">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200, damping: 15 }}
              className="mx-auto flex h-18 w-18 items-center justify-center rounded-2xl bg-gradient-to-br from-primary via-accent to-secondary shadow-lg shadow-primary/30"
            >
              <Shield className="h-9 w-9 text-white" />
            </motion.div>

            <div className="text-center">
              <CardTitle className="text-2xl font-bold text-gradient-primary">
                智慧医药推荐系统
              </CardTitle>
              <CardDescription className="mt-2 text-base">
                基于差分隐私保护的智能用药推荐平台
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            <form onSubmit={onSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="username" className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-primary" />
                  账号
                </Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="请输入账号"
                  autoComplete="username"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-secondary" />
                  密码
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="请输入密码"
                  autoComplete="current-password"
                  required
                />
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
                >
                  {error}
                </motion.div>
              )}

              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  type="submit"
                  className="relative w-full gap-2 overflow-hidden"
                  size="lg"
                  disabled={loading || isInitializing}
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>登录中...</span>
                    </>
                  ) : (
                    <>
                      <LogIn className="h-5 w-5" />
                      <span className="font-semibold">登录系统</span>
                      <Sparkles className="h-4 w-4 ml-1 opacity-70" />
                    </>
                  )}
                </Button>
              </motion.div>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-border/50" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">测试账号</span>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <motion.div
                whileHover={{ scale: 1.03, y: -2 }}
                className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-accent/5 p-4"
              >
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-primary">
                  <Stethoscope className="h-3.5 w-3.5" />
                  医生账号
                </div>
                <div className="space-y-1 text-sm">
                  <div className="font-semibold text-foreground">doctor1</div>
                  <div className="text-muted-foreground">密码：admin123</div>
                </div>
              </motion.div>

              <motion.div
                whileHover={{ scale: 1.03, y: -2 }}
                className="rounded-xl border border-secondary/20 bg-gradient-to-br from-secondary/5 to-teal-500/5 p-4"
              >
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-secondary">
                  <Shield className="h-3.5 w-3.5" />
                  管理员账号
                </div>
                <div className="space-y-1 text-sm">
                  <div className="font-semibold text-foreground">admin</div>
                  <div className="text-muted-foreground">密码：admin123</div>
                </div>
              </motion.div>
            </div>

            <div className="text-center text-sm text-muted-foreground">
              <Link
                to="/"
                className="inline-flex items-center gap-1 text-primary hover:underline hover:underline-offset-4 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                返回首页
              </Link>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="absolute bottom-4 text-center text-xs text-muted-foreground/60"
      >
        © 2024 智慧医药推荐系统 · 差分隐私保护
      </motion.div>
    </div>
  )
}
