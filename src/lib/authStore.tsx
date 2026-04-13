import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, clearAuthToken, getAuthToken, getErrorMessage, setAuthToken } from './api'

export type UserRole = 'user' | 'admin' | 'doctor'

export type AuthUser = {
  id: number
  username: string
  role: UserRole
  status: string
}

type LoginResult = { ok: true } | { ok: false; message: string }

type AuthState = {
  user: AuthUser | null
  isAuthenticated: boolean
  isInitializing: boolean
  login: (input: { username: string; password: string }) => Promise<LoginResult>
  logout: () => void
  refreshUser: () => Promise<void>
}

type BackendUser = {
  id: number
  username: string
  role: string
  status: string
}

type LoginResponse = {
  token: string
  user: BackendUser
}

const AuthContext = createContext<AuthState | null>(null)

function normalizeUser(user: BackendUser): AuthUser {
  return {
    id: user.id,
    username: user.username,
    role: user.role === 'admin' ? 'admin' : 'user',
    status: user.status,
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)

  const refreshUser = useCallback(async () => {
    const currentUser = await api.get<BackendUser>('/api/auth/me')
    setUser(normalizeUser(currentUser))
  }, [])

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      const token = getAuthToken()
      if (!token) {
        setIsInitializing(false)
        return
      }

      try {
        const currentUser = await api.get<BackendUser>('/api/auth/me')
        if (!cancelled) {
          setUser(normalizeUser(currentUser))
        }
      } catch {
        clearAuthToken()
        if (!cancelled) {
          setUser(null)
        }
      } finally {
        if (!cancelled) {
          setIsInitializing(false)
        }
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [])

  const login: AuthState['login'] = useCallback(async ({ username, password }) => {
    try {
      const response = await api.post<LoginResponse>('/api/auth/login', {
        username: username.trim(),
        password,
      })
      setAuthToken(response.token)
      setUser(normalizeUser(response.user))
      return { ok: true }
    } catch (error) {
      clearAuthToken()
      setUser(null)
      return {
        ok: false,
        message: getErrorMessage(error, '登录失败，请检查账号和密码'),
      }
    }
  }, [])

  const logout = useCallback(() => {
    clearAuthToken()
    setUser(null)
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isInitializing,
      login,
      logout,
      refreshUser,
    }),
    [isInitializing, login, logout, refreshUser, user]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
