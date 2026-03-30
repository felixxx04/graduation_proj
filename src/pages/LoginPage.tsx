import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Lock, KeyRound, LogIn } from 'lucide-react'
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
    <div className="flex min-h-[calc(100vh-0px)] items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg"
      >
        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-2xl">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-lg">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <div>
                <CardTitle className="text-2xl">登录智慧医药</CardTitle>
                <CardDescription>使用后端账号登录系统（默认账号：admin / doctor1）</CardDescription>
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
                <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full gap-2 shadow-lg" size="lg" disabled={loading || isInitializing}>
                <LogIn className="h-4 w-4" />
                {loading ? '登录中...' : '登录'}
              </Button>
            </form>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg border border-border bg-background p-3">
                <div className="mb-1 text-xs text-muted-foreground">医生</div>
                <div className="text-sm font-medium">账号：doctor1</div>
                <div className="text-sm font-medium">密码：admin123</div>
              </div>
              <div className="rounded-lg border border-border bg-background p-3">
                <div className="mb-1 text-xs text-muted-foreground">管理员</div>
                <div className="text-sm font-medium">账号：admin</div>
                <div className="text-sm font-medium">密码：admin123</div>
              </div>
            </div>

            <div className="text-center text-sm text-muted-foreground">
              登录后即可进入推荐与管理功能。{' '}
              <Link to="/" className="text-primary hover:underline">
                返回首页
              </Link>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
