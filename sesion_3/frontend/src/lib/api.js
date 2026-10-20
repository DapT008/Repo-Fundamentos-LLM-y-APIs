import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
})

// Añadir token JWT en cada petición
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirigir a login si el token expiró (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = async (username, password) => {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  const { data } = await api.post('/auth/token', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export const getMe = async () => {
  const { data } = await api.get('/auth/me')
  return data
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export const sendMessage = async (message, model = 'llama3.2') => {
  const { data } = await api.post('/api/chat', { message, model })
  return data
}

// ── Health ─────────────────────────────────────────────────────────────────────

export const getHealth = async () => {
  const { data } = await api.get('/api/health')
  return data
}

export const getCircuit = async () => {
  const { data } = await api.get('/api/health/circuit')
  return data
}

// ── Audit ─────────────────────────────────────────────────────────────────────

export const getAuditLogs = async (n = 20) => {
  const { data } = await api.get(`/api/audit/logs?n=${n}`)
  return data
}

export const verifyIntegrity = async () => {
  const { data } = await api.get('/api/audit/integrity')
  return data
}

// ── Security ──────────────────────────────────────────────────────────────────

export const scanText = async (text) => {
  const { data } = await api.post('/api/security/scan', { text })
  return data
}

// ── Architecture ──────────────────────────────────────────────────────────────

export const getCanvas = async () => {
  const { data } = await api.get('/api/architecture/canvas')
  return data
}

export const analyzeCosts = async (scenarios) => {
  const { data } = await api.post('/api/architecture/costs', { scenarios })
  return data
}

export default api
