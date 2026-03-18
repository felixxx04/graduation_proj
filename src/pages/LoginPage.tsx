import { useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Lock, KeyRound, LogIn } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/lib/authStore'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as any

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const from = useMemo(() => {
    const v = location?.state?.from
    return typeof v === 'string' && v.length ? v : '/'
  }, [location?.state?.from])

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setTimeout(() => {
      const res = login({ username, password })
      setLoading(false)
      if (!res.ok) {
        setError(res.message)
        return
      }
      navigate(from, { replace: true })
    }, 450)
  }

  return (
    <div className="min-h-[calc(100vh-0px)] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg"
      >
        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-2xl">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <div>
                <CardTitle className="text-2xl">登录智医荐药</CardTitle>
                <CardDescription>使用前请先登录（demo：普通用户/管理员）</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username" className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-primary" />
                  账号
                </Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="user 或 admin"
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
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="123456"
                  autoComplete="current-password"
                  required
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 text-sm">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full gap-2 shadow-lg" size="lg" disabled={loading}>
                <LogIn className="h-4 w-4" />
                {loading ? '登录中...' : '登录'}
              </Button>
            </form>

            <div className="grid md:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-background border border-border">
                <div className="text-xs text-muted-foreground mb-1">普通用户</div>
                <div className="text-sm font-medium">账号：user</div>
                <div className="text-sm font-medium">密码：123456</div>
              </div>
              <div className="p-3 rounded-lg bg-background border border-border">
                <div className="text-xs text-muted-foreground mb-1">管理员</div>
                <div className="text-sm font-medium">账号：admin</div>
                <div className="text-sm font-medium">密码：123456</div>
              </div>
            </div>

            <div className="text-sm text-muted-foreground text-center">
              登录后可进入首页与推荐系统。想先看看页面？{' '}
              <Link to="/login" className="text-primary hover:underline">
                刷新保持在登录页
              </Link>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

