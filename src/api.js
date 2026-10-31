import axios from 'axios'
import { getAccessToken, setAccessToken } from './auth/token'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshRequest = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const isAuthRequest =
      typeof original?.url === 'string' && original.url.includes('/auth/')

    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      isAuthRequest
    ) {
      return Promise.reject(error)
    }

    original._retry = true
    try {
      refreshRequest = refreshRequest || api.post('/auth/refresh')
      const { data } = await refreshRequest
      refreshRequest = null
      setAccessToken(data.access_token)
      original.headers.Authorization = `Bearer ${data.access_token}`
      return api(original)
    } catch (refreshError) {
      refreshRequest = null
      setAccessToken(null)
      window.dispatchEvent(new Event('auth:expired'))
      return Promise.reject(error)
    }
  },
)

export const getResource = async (path, fallback) => {
  try {
    return (await api.get(path)).data
  } catch {
    return fallback
  }
}
