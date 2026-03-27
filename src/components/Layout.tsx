import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Activity,
  Users,
  Shield,
  Stethoscope,
  BarChart3,
  Settings,
  Menu,
  X,
  LogOut,
  User as UserIcon,
  LogIn,
  Lock,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/lib/authStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { canAccessFeature } from '@/lib/permissions'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout, login, isInitializing } = useAuth()

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState(false)
  const [pendingPath, setPendingPath] = useState('/')

  const navigation = useMemo(
    () => [
      { name: '首页', href: '/', icon: Activity },
      ...(canAccessFeature(user?.role, 'patients') ? [{ name: '患者档案', href: '/patients', icon: Users }] : []),
      ...(canAccessFeature(user?.role, 'privacy') ? [{ name: '隐私配置', href: '/privacy', icon: Shield }] : []),
      ...(canAccessFeature(user?.role, 'recommendation') ? [{ name: '用药推荐', href: '/recommendation', icon: Stethoscope }] : []),
      ...(canAccessFeature(user?.role, 'visualization') ? [{ name: '效果可视化', href: '/visualization', icon: BarChart3 }] : []),
      ...(canAccessFeature(user?.role, 'admin') ? [{ name: '后台管理', href: '/admin', icon: Settings }] : []),
    ],
    [user?.role]
  )

  useEffect(() => {
    const state = (location as { state?: { loginModal?: boolean; from?: string } }).state
    if (isInitializing || !state?.loginModal) {
      return
    }

    setPendingPath(typeof state.from === 'string' ? state.from : '/')
    setLoginModalOpen(true)
    navigate(location.pathname, { replace: true })
  }, [isInitializing, location, navigate])

  const closeModal = () => {
    setLoginModalOpen(false)
    setLoginError(null)
    setLoginLoading(false)
    setLoginUsername('')
    setLoginPassword('')
  }

  const openLoginModal = (path = '/') => {
    setPendingPath(path)
    setLoginError(null)
    setLoginModalOpen(true)
  }

  const onLogout = () => {
    logout()
    setMobileMenuOpen(false)
    closeModal()
    navigate('/', { replace: true })
  }

  const onSubmitLogin = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoginError(null)
    setLoginLoading(true)

    const result = await login({ username: loginUsername, password: loginPassword })
    setLoginLoading(false)

    if (!result.ok) {
      setLoginError(result.message)
      return
    }

    setLoginModalOpen(false)
    navigate(pendingPath || '/', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50 dark:from-slate-950 dark:via-blue-950 dark:to-teal-950">
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-lg">
              <Activity className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-xl font-bold text-transparent">
                智慧医药
              </h1>
              <p className="text-xs text-muted-foreground">差分隐私保护的个性化用药推荐系统</p>
            </div>
          </div>

          <nav className="hidden flex-1 items-center justify-center gap-1 md:flex">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-gradient-to-r from-primary/10 to-secondary/10 text-primary shadow-sm'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className={cn('h-4 w-4', isActive && 'text-primary')} />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          <div className="hidden items-center gap-2 md:flex">
            {isInitializing ? (
              <div className="px-3 py-2 text-sm text-muted-foreground">验证登录状态中...</div>
            ) : user ? (
              <>
                <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2">
                  <UserIcon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{user.username}</span>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                    {user.role === 'admin' ? '管理员' : '普通用户'}
                  </span>
                </div>
                <button
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
                  onClick={onLogout}
                >
                  <LogOut className="h-4 w-4" />
                  退出
                </button>
              </>
            ) : (
              <Button className="gap-2" onClick={() => openLoginModal('/')}>
                <LogIn className="h-4 w-4" />
                登录
              </Button>
            )}
          </div>

          <button
            className="rounded-lg p-2 hover:bg-muted md:hidden"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="animate-in slide-in-from-top-2 space-y-2 border-t border-border bg-background p-4 md:hidden">
            {user ? (
              <div className="mb-2 flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 p-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{user.username}</div>
                  <div className="text-xs text-muted-foreground">{user.role === 'admin' ? '管理员' : '普通用户'}</div>
                </div>
                <button
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
                  onClick={onLogout}
                >
                  <LogOut className="h-4 w-4" />
                  退出
                </button>
              </div>
            ) : (
              <div className="mb-2 flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 p-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">未登录</div>
                  <div className="text-xs text-muted-foreground">登录后可使用完整功能</div>
                </div>
                <button
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
                  onClick={() => {
                    openLoginModal('/')
                    setMobileMenuOpen(false)
                  }}
                >
                  <LogIn className="h-4 w-4" />
                  登录
                </button>
              </div>
            )}

            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-gradient-to-r from-primary/10 to-secondary/10 text-primary shadow-sm'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Icon className={cn('h-5 w-5', isActive && 'text-primary')} />
                  {item.name}
                </Link>
              )
            })}
          </div>
        )}
      </header>

      {loginModalOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeModal()
            }
          }}
        >
          <div className="w-full max-w-lg">
            <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-2xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl">
                  <Lock className="h-5 w-5 text-primary" />
                  登录后继续
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  你正在访问受保护页面：<span className="font-medium text-foreground">{pendingPath}</span>
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={onSubmitLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="modal-username">账号</Label>
                    <Input
                      id="modal-username"
                      value={loginUsername}
                      onChange={(event) => setLoginUsername(event.target.value)}
                      placeholder="请输入账号"
                      autoComplete="username"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="modal-password">密码</Label>
                    <Input
                      id="modal-password"
                      type="password"
                      value={loginPassword}
                      onChange={(event) => setLoginPassword(event.target.value)}
                      placeholder="请输入密码"
                      autoComplete="current-password"
                      required
                    />
                  </div>

                  {loginError && (
                    <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                      {loginError}
                    </div>
                  )}

                  <div className="flex gap-3">
                    <Button type="submit" className="flex-1 gap-2" disabled={loginLoading || isInitializing}>
                      <LogIn className="h-4 w-4" />
                      {loginLoading ? '登录中...' : '登录'}
                    </Button>
                    <Button type="button" variant="outline" className="flex-1" onClick={closeModal}>
                      取消
                    </Button>
                  </div>
                </form>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-border bg-background p-3">
                    <div className="mb-1 text-xs text-muted-foreground">普通用户</div>
                    <div className="text-sm font-medium">user / 123456</div>
                  </div>
                  <div className="rounded-lg border border-border bg-background p-3">
                    <div className="mb-1 text-xs text-muted-foreground">管理员</div>
                    <div className="text-sm font-medium">admin / 123456</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <main className="container py-8">
        <Outlet />
      </main>

      <footer className="mt-auto border-t border-border/40 bg-background/50 backdrop-blur">
        <div className="container py-6">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-secondary">
                <Activity className="h-4 w-4 text-white" />
              </div>
              <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-sm font-medium text-transparent">
                智慧医药
              </span>
            </div>
            <p className="text-center text-sm text-muted-foreground md:text-right">
              基于差分隐私的 AI 个性化医疗用药推荐系统 · 保护隐私 · 精准推荐
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
