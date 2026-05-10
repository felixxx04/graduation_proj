import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth, type UserRole } from '@/lib/authStore'

function AuthLoading() {
  return <div className="py-16 text-center text-sm text-muted-foreground">正在验证登录状态...</div>
}

export function RequireAuth() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()

  if (isInitializing) return <AuthLoading />
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function RequireAuthModal() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()

  if (isInitializing) return <AuthLoading />
  if (!isAuthenticated) return <Navigate to="/" replace state={{ loginModal: true, from: location.pathname }} />
  return <Outlet />
}

export function RequireRole({ role, roles }: { role?: UserRole; roles?: UserRole[] }) {
  const { user, isInitializing } = useAuth()
  const location = useLocation()
  const allowedRoles = roles || (role ? [role] : [])

  if (isInitializing) return <AuthLoading />
  if (!user) return <Navigate to="/" replace state={{ loginModal: true, from: location.pathname }} />
  if (!allowedRoles.includes(user.role)) return <Navigate to="/forbidden" replace />
  return <Outlet />
}
