import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { getCurrentUser, login as loginRequest, logout as logoutRequest, register as registerRequest } from '../services/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const handleUnauthorized = () => {
      localStorage.removeItem('brightloop_access_token')
      setUser(null)
    }
    window.addEventListener('brightloop:unauthorized', handleUnauthorized)
    const token = localStorage.getItem('brightloop_access_token')
    if (!token) {
      setLoading(false)
      return () => window.removeEventListener('brightloop:unauthorized', handleUnauthorized)
    }
    getCurrentUser()
      .then(({ data }) => setUser(data))
      .catch(handleUnauthorized)
      .finally(() => setLoading(false))
    return () => window.removeEventListener('brightloop:unauthorized', handleUnauthorized)
  }, [])

  const login = async (payload) => {
    const { data } = await loginRequest(payload)
    localStorage.setItem('brightloop_access_token', data.access_token)
    setUser(data.user)
    return data.user
  }

  const register = async (payload) => {
    const { data } = await registerRequest(payload)
    localStorage.setItem('brightloop_access_token', data.access_token)
    setUser(data.user)
    return data.user
  }

  const logout = async () => {
    try { await logoutRequest() } finally {
      localStorage.removeItem('brightloop_access_token')
      setUser(null)
    }
  }

  const value = useMemo(() => ({ user, loading, login, register, logout, setUser }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
