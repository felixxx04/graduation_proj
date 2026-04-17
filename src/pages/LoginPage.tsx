import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Shield, Lock, KeyRound, LogIn, ArrowLeft } from 'lucide-react'
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
    <div className="flex min-h-screen items-center justify-center p-4">
      {/* Login Card */}
      <div className="w-full max-w-sm animate-fade-in">
        <Card hover="none">
          <CardHeader>
            <div className="flex items-center gap-3 mb-1">
              <div className="flex h-10 w-10 items-center justify-center rounded-standard bg-primary">
                <Shield className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <CardTitle>智医荐药</CardTitle>
                <CardDescription>基于差分隐私保护的智能用药推荐平台</CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-ia-caption font-heading font-semibold">
                  账号
                </Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="请输入账号"
                  autoComplete="username"
                  required
                  icon={<KeyRound className="h-4 w-4" />}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-ia-caption font-heading font-semibold">
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
                  icon={<Lock className="h-4 w-4" />}
                />
              </div>

              {error && (
                <div className="rounded-standard border border-destructive/30 bg-destructive/6 p-2.5 text-ia-caption text-destructive">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full gap-2"
                size="lg"
                loading={loading}
                disabled={isInitializing}
              >
                <LogIn className="h-4 w-4" />
                登录系统
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-ia-border" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-card px-2 text-ia-label text-muted-foreground">测试账号</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-standard border border-ia-border p-2.5">
                <div className="text-ia-label text-muted-foreground mb-1">医生账号</div>
                <div className="text-ia-caption font-heading font-semibold">doctor1</div>
                <div className="text-ia-label text-muted-foreground">admin123</div>
              </div>
              <div className="rounded-standard border border-ia-border p-2.5">
                <div className="text-ia-label text-muted-foreground mb-1">管理员</div>
                <div className="text-ia-caption font-heading font-semibold">admin</div>
                <div className="text-ia-label text-muted-foreground">admin123</div>
              </div>
            </div>

            <div className="text-center">
              <Link
                to="/"
                className="inline-flex items-center gap-1 text-ia-caption text-primary hover:underline hover:underline-offset-4 transition-colors cursor-pointer"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                返回首页
              </Link>
            </div>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-ia-label text-muted-foreground">
          &copy; 2024 智医荐药 · 差分隐私保护的智能用药推荐系统
        </p>
      </div>
    </div>
  )
}
