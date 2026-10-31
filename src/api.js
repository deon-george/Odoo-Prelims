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

export function formatApiError(error, fallback = 'Something went wrong.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.detail || 'Invalid value.')
      .join(' ')
  }
  return error?.message || fallback
}

export const listProducts = async (params = {}) =>
  (await api.get('/products', { params })).data

export const createProduct = async (payload) =>
  (await api.post('/products', payload)).data

export const updateProduct = async (id, payload) =>
  (await api.patch(`/products/${id}`, payload)).data

export const setProductStatus = async (id, status) =>
  (await api.patch(`/products/${id}/status`, { status })).data

export const listPlans = async (params = {}) =>
  (await api.get('/plans', { params })).data

export const createPlan = async (payload) =>
  (await api.post('/plans', payload)).data

export const updatePlan = async (id, payload) =>
  (await api.patch(`/plans/${id}`, payload)).data

export const setPlanStatus = async (id, status) =>
  (await api.patch(`/plans/${id}/status`, { status })).data
