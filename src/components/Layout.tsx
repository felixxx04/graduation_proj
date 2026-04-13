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
  Sparkles,
  Heart,
  ChevronRight,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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
  const [scrolled, setScrolled] = useState(false)

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
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

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
    <div className="min-h-screen bg-mesh-gradient">
      {/* Background Pattern */}
      <div className="fixed inset-0 bg-medical-dna opacity-40 pointer-events-none" />

      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className={cn(
          "sticky top-0 z-50 w-full transition-all duration-300",
          scrolled
            ? "glass border-b border-border/30"
            : "bg-transparent"
        )}
      >
        <div className="container flex h-16 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-accent to-secondary shadow-lg shadow-primary/30 group-hover:shadow-xl group-hover:shadow-primary/40 transition-all duration-300">
                <Heart className="h-5 w-5 text-white" />
              </div>
              <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-success rounded-full border-2 border-background animate-pulse" />
            </div>
            <div>
              <h1 className="text-gradient-primary text-xl font-bold tracking-tight">
                智慧医药
              </h1>
              <p className="text-[10px] text-muted-foreground leading-tight">隐私保护 · 智能推荐</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex flex-1 items-center justify-center gap-1">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'relative flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  )}
                >
                  <Icon className={cn('h-4 w-4', isActive && 'text-primary')} />
                  {item.name}
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute inset-0 bg-primary/10 rounded-xl -z-10"
                      transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </Link>
              )
            })}
          </nav>

          {/* User Section */}
          <div className="hidden lg:flex items-center gap-3">
            {isInitializing ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                验证中...
              </div>
            ) : user ? (
              <>
                <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card/50 backdrop-blur px-4 py-2">
                  <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-accent">
                    <UserIcon className="h-4 w-4 text-white" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold truncate">{user.username}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {user.role === 'admin' ? '管理员' : user.role === 'doctor' ? '医生' : '研究员'}
                    </div>
                  </div>
                </div>
                <button
                  className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-destructive/10 hover:text-destructive"
                  onClick={onLogout}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </>
            ) : (
              <Button
                onClick={() => openLoginModal('/')}
                className="gap-2"
                size="default"
              >
                <LogIn className="h-4 w-4" />
                登录
              </Button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="lg:hidden rounded-xl p-2 hover:bg-muted transition-colors"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="lg:hidden border-t border-border/30 glass"
            >
              <div className="container py-4 space-y-2">
                {user && (
                  <div className="flex items-center justify-between gap-3 rounded-xl border border-border/50 bg-card/50 p-3 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent">
                        <UserIcon className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <div className="font-semibold">{user.username}</div>
                        <div className="text-xs text-muted-foreground">
                          {user.role === 'admin' ? '管理员' : user.role === 'doctor' ? '医生' : '研究员'}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={onLogout}
                      className="p-2 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    >
                      <LogOut className="h-5 w-5" />
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
                        'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all',
                        isActive
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )}
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <Icon className="h-5 w-5" />
                      {item.name}
                      <ChevronRight className={cn('h-4 w-4 ml-auto', isActive ? 'opacity-100' : 'opacity-0')} />
                    </Link>
                  )
                })}

                {!user && (
                  <Button
                    onClick={() => {
                      openLoginModal('/')
                      setMobileMenuOpen(false)
                    }}
                    className="w-full gap-2 mt-4"
                  >
                    <LogIn className="h-4 w-4" />
                    登录
                  </Button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      {/* Login Modal */}
      <AnimatePresence>
        {loginModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && closeModal()}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md"
            >
              <Card className="border-0 shadow-2xl overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-accent/5 to-secondary/5" />
                <div className="relative z-10">
                  <CardHeader className="text-center pb-2">
                    <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mb-4 shadow-lg shadow-primary/30">
                      <Lock className="h-8 w-8 text-white" />
                    </div>
                    <CardTitle className="text-2xl">登录后继续</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      访问页面：<span className="font-medium text-foreground">{pendingPath}</span>
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
                          onChange={(e) => setLoginPassword(e.target.value)}
                          placeholder="请输入密码"
                          autoComplete="current-password"
                          required
                        />
                      </div>

                      {loginError && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
                        >
                          {loginError}
                        </motion.div>
                      )}

                      <div className="flex gap-3 pt-2">
                        <Button
                          type="submit"
                          className="flex-1"
                          disabled={loginLoading || isInitializing}
                        >
                          {loginLoading ? (
                            <>
                              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              登录中...
                            </>
                          ) : (
                            <>
                              <Sparkles className="h-4 w-4" />
                              登录
                            </>
                          )}
                        </Button>
                        <Button type="button" variant="outline" className="flex-1" onClick={closeModal}>
                          取消
                        </Button>
                      </div>
                    </form>

                    <div className="grid grid-cols-2 gap-3 pt-2">
                      <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-accent/5 p-3 text-center">
                        <div className="text-[10px] text-muted-foreground mb-1">医生账号</div>
                        <div className="text-sm font-semibold">doctor1</div>
                        <div className="text-xs text-muted-foreground">admin123</div>
                      </div>
                      <div className="rounded-xl border border-secondary/20 bg-gradient-to-br from-secondary/5 to-teal-500/5 p-3 text-center">
                        <div className="text-[10px] text-muted-foreground mb-1">管理员</div>
                        <div className="text-sm font-semibold">admin</div>
                        <div className="text-xs text-muted-foreground">admin123</div>
                      </div>
                    </div>
                  </CardContent>
                </div>
              </Card>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="container py-8 relative z-10">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="relative z-10 mt-auto border-t border-border/30 glass">
        <div className="container py-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-md">
                <Heart className="h-5 w-5 text-white" />
              </div>
              <div>
                <span className="text-gradient-primary text-sm font-bold">
                  智慧医药
                </span>
                <p className="text-[10px] text-muted-foreground">差分隐私保护的智能用药推荐系统</p>
              </div>
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
