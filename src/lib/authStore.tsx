import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type UserRole = 'user' | 'admin'

export type AuthUser = {
  username: string
  role: UserRole
}

type AuthState = {
  user: AuthUser | null
  isAuthenticated: boolean
  login: (input: { username: string; password: string }) => { ok: true } | { ok: false; message: string }
  logout: () => void
}

const STORAGE_KEY = 'dp_med_demo_auth_v1'

type Persisted = {
  user: AuthUser | null
}

const AuthContext = createContext<AuthState | null>(null)

function safeParse(json: string | null): Persisted | null {
  if (!json) return null
  try {
    return JSON.parse(json) as Persisted
  } catch {
    return null
  }
}

// Demo users (frontend-only). Backend will replace this later.
const DEMO_ACCOUNTS: Array<{ username: string; password: string; role: UserRole }> = [
  { username: 'user', password: '123456', role: 'user' },
  { username: 'admin', password: '123456', role: 'admin' },
]

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)

  useEffect(() => {
    const persisted = safeParse(localStorage.getItem(STORAGE_KEY))
    if (persisted?.user) setUser(persisted.user)
  }, [])

  useEffect(() => {
    const persisted: Persisted = { user }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted))
  }, [user])

  const login: AuthState['login'] = ({ username, password }) => {
    const u = username.trim()
    const account = DEMO_ACCOUNTS.find((a) => a.username === u && a.password === password)
    if (!account) return { ok: false, message: '账号或密码错误（demo：user/admin，密码均为 123456）' }
    setUser({ username: account.username, role: account.role })
    return { ok: true }
  }

  const logout = () => setUser(null)

  const value = useMemo<AuthState>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      login,
      logout,
    }),
    [user]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

