import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth, type UserRole } from '@/lib/authStore'

export function RequireAuth() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

export function RequireAuthModal() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/" replace state={{ loginModal: true, from: location.pathname }} />
  }

  return <Outlet />
}

export function RequireRole({ role }: { role: UserRole }) {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) return <Navigate to="/" replace state={{ loginModal: true, from: location.pathname }} />
  if (user.role !== role) return <Navigate to="/forbidden" replace />

  return <Outlet />
}

