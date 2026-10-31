import axios from 'axios'
export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api' })
export const getResource = async (path, fallback) => { try { return (await api.get(path)).data } catch { return fallback } }
