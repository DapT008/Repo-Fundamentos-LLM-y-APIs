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

let isRefreshing = false
let refreshSubscribers = []

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb)
}

function notifySubscribers(token) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

// Intentar refresh antes de redirigir a login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh((newToken) => {
          if (newToken) {
            original.headers.Authorization = `Bearer ${newToken}`
            resolve(api(original))
          } else {
            reject(error)
          }
        })
      })
    }

    original._retry = true
    isRefreshing = true

    try {
      const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`
      notifySubscribers(data.access_token)
      original.headers.Authorization = `Bearer ${data.access_token}`
      return api(original)
    } catch {
      clearTokens()
      notifySubscribers(null)
      window.location.href = '/login'
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
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

export const sendMessage = async (message, model = 'llama3.2:3b') => {
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
