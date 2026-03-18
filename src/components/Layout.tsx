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
  Lock
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

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

  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState(false)
  const [pendingPath, setPendingPath] = useState<string>('/')

  const { login } = useAuth()

  useEffect(() => {
    const state = (location as any)?.state
    if (state?.loginModal) {
      setPendingPath(typeof state?.from === 'string' ? state.from : '/')
      setLoginModalOpen(true)
      // Clear the state so refresh/back doesn't re-trigger
      navigate(location.pathname, { replace: true })
    }
  }, [location, navigate])

  const onLogout = () => {
    logout()
    setMobileMenuOpen(false)
    navigate('/', { replace: true })
  }

  const closeModal = () => {
    setLoginModalOpen(false)
    setLoginError(null)
    setLoginLoading(false)
  }

  const onSubmitLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError(null)
    setLoginLoading(true)
    setTimeout(() => {
      const res = login({ username: loginUsername, password: loginPassword })
      setLoginLoading(false)
      if (!res.ok) {
        setLoginError(res.message)
        return
      }
      setLoginModalOpen(false)
      navigate(pendingPath || '/', { replace: true })
    }, 350)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50 dark:from-slate-950 dark:via-blue-950 dark:to-teal-950">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-sm">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg">
              <Activity className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                智医荐药
              </h1>
              <p className="text-xs text-muted-foreground">隐私保护的智能用药推荐系统</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 flex-1 justify-center">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-gradient-to-r from-primary/10 to-secondary/10 text-primary shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  )}
                >
                  <Icon className={cn('h-4 w-4', isActive && 'text-primary')} />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User actions */}
          <div className="hidden md:flex items-center gap-2">
            {user ? (
              <>
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border border-border">
                  <UserIcon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{user.username}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                    {user.role === 'admin' ? '管理员' : '普通用户'}
                  </span>
                </div>
                <button
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                  onClick={onLogout}
                >
                  <LogOut className="h-4 w-4" />
                  退出
                </button>
              </>
            ) : (
              <Button className="gap-2" onClick={() => { setPendingPath('/'); setLoginModalOpen(true) }}>
                <LogIn className="h-4 w-4" />
                登录
              </Button>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 rounded-lg hover:bg-muted"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border p-4 space-y-2 bg-background animate-in slide-in-from-top-2">
            {user ? (
              <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-muted/40 border border-border mb-2">
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{user.username}</div>
                  <div className="text-xs text-muted-foreground">{user.role === 'admin' ? '管理员' : '普通用户'}</div>
                </div>
                <button
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                  onClick={onLogout}
                >
                  <LogOut className="h-4 w-4" />
                  退出
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-muted/40 border border-border mb-2">
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">未登录</div>
                  <div className="text-xs text-muted-foreground">登录后可使用完整功能</div>
                </div>
                <button
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                  onClick={() => {
                    setPendingPath('/')
                    setLoginModalOpen(true)
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
                    'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-gradient-to-r from-primary/10 to-secondary/10 text-primary shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
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

      {/* Login Modal */}
      {loginModalOpen && (
        <div
          className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeModal()
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
                  你正在访问受保护功能：<span className="font-medium text-foreground">{pendingPath}</span>
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={onSubmitLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="modal-username">账号</Label>
                    <Input
                      id="modal-username"
                      value={loginUsername}
                      onChange={(e) => setLoginUsername(e.target.value)}
                      placeholder="user 或 admin"
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
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="123456"
                      autoComplete="current-password"
                      required
                    />
                  </div>

                  {loginError && (
                    <div className="p-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 text-sm">
                      {loginError}
                    </div>
                  )}

                  <div className="flex gap-3">
                    <Button type="submit" className="flex-1 gap-2" disabled={loginLoading}>
                      <LogIn className="h-4 w-4" />
                      {loginLoading ? '登录中...' : '登录'}
                    </Button>
                    <Button type="button" variant="outline" className="flex-1" onClick={closeModal}>
                      取消
                    </Button>
                  </div>
                </form>

                <div className="grid md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground mb-1">普通用户</div>
                    <div className="text-sm font-medium">user / 123456</div>
                  </div>
                  <div className="p-3 rounded-lg bg-background border border-border">
                    <div className="text-xs text-muted-foreground mb-1">管理员</div>
                    <div className="text-sm font-medium">admin / 123456</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="container py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 bg-background/50 backdrop-blur mt-auto">
        <div className="container py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                <Activity className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-medium bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                智医荐药
              </span>
            </div>
            <p className="text-sm text-muted-foreground text-center md:text-right">
              基于差分隐私的医疗用药推荐系统 · 保护隐私 · 精准推荐
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
