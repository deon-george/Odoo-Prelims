import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { setAccessToken } from './token'

const AuthContext = createContext(null)

// Deduplicate the restore call (React StrictMode runs effects twice in dev).
let restorePromise = null

function restoreSession() {
  if (!restorePromise) {
    restorePromise = api
      .post('/auth/refresh')
      .then(({ data }) => {
        setAccessToken(data.access_token)
        return data.user
      })
      .finally(() => {
        restorePromise = null
      })
  }
  return restorePromise
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [initializing, setInitializing] = useState(true)

  useEffect(() => {
    let cancelled = false

    restoreSession()
      .then((restoredUser) => {
        if (!cancelled) setUser(restoredUser)
      })
      .catch(() => {
        if (!cancelled) {
          setAccessToken(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) setInitializing(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const handleExpired = () => {
      setAccessToken(null)
      setUser(null)
    }
    window.addEventListener('auth:expired', handleExpired)
    return () => window.removeEventListener('auth:expired', handleExpired)
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    setAccessToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async ({ full_name, email, password }) => {
    const { data } = await api.post('/auth/register', {
      full_name,
      email,
      password,
    })
    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // The local session is cleared even if the server is unreachable.
    }
    setAccessToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, initializing, login, register, logout }),
    [user, initializing, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
