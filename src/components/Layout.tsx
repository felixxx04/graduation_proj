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
  Heart,
  ChevronRight,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
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
    <div className="min-h-screen bg-background">
      {/* Header — Border-based, no glass */}
      <header className="sticky top-0 z-50 w-full border-b border-ia-border bg-card/95">
        <div className="container flex h-14 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 cursor-pointer group">
            <div className="flex h-8 w-8 items-center justify-center rounded-standard bg-primary">
              <Heart className="h-4 w-4 text-primary-foreground" />
            </div>
            <div>
              <span className="text-ia-body font-heading font-bold tracking-tight text-foreground">
                智医荐药
              </span>
              <span className="hidden sm:inline text-ia-label text-muted-foreground ml-2">
                隐私保护 · 智能推荐
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex flex-1 items-center justify-center gap-0.5">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-1.5 rounded-standard px-3 py-1.5 text-ia-caption font-heading font-medium transition-colors duration-150 cursor-pointer',
                    isActive
                      ? 'bg-primary/8 text-primary border border-primary/20'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted border border-transparent'
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User Section */}
          <div className="hidden lg:flex items-center gap-2">
            {isInitializing ? (
              <div className="flex items-center gap-1.5 text-ia-caption text-muted-foreground">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                验证中
              </div>
            ) : user ? (
              <>
                <div className="flex items-center gap-2 rounded-standard border border-ia-border bg-card px-3 py-1.5">
                  <div className="flex items-center justify-center w-6 h-6 rounded-micro bg-primary">
                    <UserIcon className="h-3.5 w-3.5 text-primary-foreground" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-ia-caption font-heading font-semibold truncate leading-none">{user.username}</div>
                    <div className="text-ia-label text-muted-foreground leading-none mt-0.5">
                      {user.role === 'admin' ? '管理员' : user.role === 'doctor' ? '医生' : '研究员'}
                    </div>
                  </div>
                </div>
                <button
                  className="flex items-center gap-1.5 rounded-standard px-2 py-1.5 text-ia-caption font-medium text-muted-foreground transition-colors duration-150 hover:bg-destructive/8 hover:text-destructive cursor-pointer"
                  onClick={onLogout}
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </>
            ) : (
              <Button
                onClick={() => openLoginModal('/')}
                className="gap-1.5"
                size="sm"
              >
                <LogIn className="h-3.5 w-3.5" />
                登录
              </Button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="lg:hidden rounded-standard p-2 hover:bg-muted transition-colors duration-150 cursor-pointer"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <div className="lg:hidden border-t border-ia-border bg-card">
              <div className="container py-3 space-y-0.5">
                {user && (
                  <div className="flex items-center justify-between gap-2 rounded-standard border border-ia-border bg-card p-2.5 mb-3">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center justify-center w-8 h-8 rounded-standard bg-primary">
                        <UserIcon className="h-4 w-4 text-primary-foreground" />
                      </div>
                      <div>
                        <div className="text-ia-body font-heading font-semibold">{user.username}</div>
                        <div className="text-ia-label text-muted-foreground">
                          {user.role === 'admin' ? '管理员' : user.role === 'doctor' ? '医生' : '研究员'}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={onLogout}
                      className="p-1.5 rounded-standard text-muted-foreground hover:bg-destructive/8 hover:text-destructive cursor-pointer"
                    >
                      <LogOut className="h-4 w-4" />
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
                        'flex items-center gap-2.5 rounded-standard px-3 py-2 text-ia-body font-medium transition-colors duration-150 cursor-pointer',
                        isActive
                          ? 'bg-primary/8 text-primary border-l-2 border-l-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground border-l-2 border-l-transparent'
                      )}
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <Icon className="h-4 w-4" />
                      {item.name}
                      <ChevronRight className={cn('h-3.5 w-3.5 ml-auto', isActive ? 'opacity-70' : 'opacity-0')} />
                    </Link>
                  )
                })}

                {!user && (
                  <Button
                    onClick={() => {
                      openLoginModal('/')
                      setMobileMenuOpen(false)
                    }}
                    className="w-full gap-1.5 mt-3"
                    size="default"
                  >
                    <LogIn className="h-4 w-4" />
                    登录
                  </Button>
                )}
              </div>
            </div>
          )}
        </AnimatePresence>
      </header>

      {/* Login Modal — Border-based, clinical precision */}
      <AnimatePresence>
        {loginModalOpen && (
          <div
            className="fixed inset-0 z-[60] flex items-center justify-center bg-foreground/20 p-4"
            onClick={(e) => e.target === e.currentTarget && closeModal()}
          >
            <div className="w-full max-w-sm animate-fade-in">
              <Card hover="none">
                <CardHeader>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-standard bg-primary">
                      <Lock className="h-4 w-4 text-primary-foreground" />
                    </div>
                    <div>
                      <CardTitle>登录后继续</CardTitle>
                      <p className="text-ia-caption text-muted-foreground mt-0.5">
                        目标页面：<span className="font-medium text-foreground font-heading">{pendingPath}</span>
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <form onSubmit={onSubmitLogin} className="space-y-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="modal-username" className="text-ia-caption font-heading font-semibold">账号</Label>
                      <Input
                        id="modal-username"
                        value={loginUsername}
                        onChange={(e) => setLoginUsername(e.target.value)}
                        placeholder="请输入账号"
                        autoComplete="username"
                        required
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="modal-password" className="text-ia-caption font-heading font-semibold">密码</Label>
                      <Input
                        id="modal-password"
                        type="password"
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        placeholder="请输入密码"
                        autoComplete="current-password"
                        required
                      />
                    </div>

                    {loginError && (
                      <div className="rounded-standard border border-destructive/30 bg-destructive/6 p-2.5 text-ia-caption text-destructive">
                        {loginError}
                      </div>
                    )}

                    <div className="flex gap-2 pt-1">
                      <Button
                        type="submit"
                        className="flex-1"
                        loading={loginLoading}
                        disabled={isInitializing}
                      >
                        登录
                      </Button>
                      <Button type="button" variant="outline" className="flex-1" onClick={closeModal}>
                        取消
                      </Button>
                    </div>
                  </form>

                  <div className="grid grid-cols-2 gap-2 pt-1">
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
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="container py-6">
        <Outlet />
      </main>

      {/* Footer — Border top, no glass */}
      <footer className="border-t border-ia-border bg-card mt-auto">
        <div className="container py-6">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-standard bg-primary">
                <Heart className="h-3.5 w-3.5 text-primary-foreground" />
              </div>
              <div>
                <span className="text-ia-caption font-heading font-bold text-foreground">
                  智医荐药
                </span>
                <span className="text-ia-label text-muted-foreground ml-2">
                  差分隐私保护的智能用药推荐系统
                </span>
              </div>
            </div>
            <p className="text-ia-label text-muted-foreground text-center md:text-right">
              基于差分隐私的 AI 个性化医疗用药推荐系统 · 保护隐私 · 精准推荐
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
