import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import { Lock } from 'lucide-react'

const C = {
  bg: '#0F1923',
  panel: '#1A2838',
  cyan: '#00D4FF',
  gold: '#F5A623',
  text: '#E0E8F0',
  muted: '#7A95AA',
  border: '#2a3f54',
  error: '#ff5252',
}

const DEMO_USERS = [
  { email: 'admin@techcorp.com', password: 'admin123', role: 'Admin (read/write/admin)' },
  { email: 'dev@techcorp.com',   password: 'dev123',   role: 'Dev (read/write)' },
  { email: 'readonly@techcorp.com', password: 'read123', role: 'Readonly (read)' },
]

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/chat')
    } catch (err) {
      setError(err.response?.data?.detail || 'Credenciales incorrectas')
    } finally {
      setLoading(false)
    }
  }

  const quickLogin = (user) => {
    setEmail(user.email)
    setPassword(user.password)
  }

  return (
    <div style={styles.root}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.icon}><Lock size={28} color={C.cyan} /></div>
          <h1 style={styles.title}>LLM Security Lab</h1>
          <p style={styles.subtitle}>Sesión 3 · Seguridad y Alta Disponibilidad</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>Email</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="admin@techcorp.com"
            required
            style={styles.input}
          />

          <label style={styles.label}>Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            style={styles.input}
          />

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" disabled={loading} style={styles.btn}>
            {loading ? 'Autenticando...' : 'Iniciar Sesión'}
          </button>
        </form>

        <div style={styles.demoSection}>
          <p style={styles.demoTitle}>Usuarios de demostración:</p>
          {DEMO_USERS.map(u => (
            <button
              key={u.email}
              onClick={() => quickLogin(u)}
              style={styles.demoBtn}
            >
              <span style={{ color: C.cyan }}>{u.email}</span>
              <span style={{ color: C.muted, fontSize: '0.75rem' }}>{u.role}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

const styles = {
  root: {
    minHeight: '100vh',
    background: C.bg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
  },
  card: {
    background: C.panel,
    border: `1px solid ${C.border}`,
    borderRadius: 12,
    padding: 32,
    width: '100%',
    maxWidth: 420,
  },
  header: {
    textAlign: 'center',
    marginBottom: 28,
  },
  icon: {
    marginBottom: 12,
  },
  title: {
    color: C.text,
    fontSize: '1.4rem',
    fontWeight: 700,
    margin: 0,
  },
  subtitle: {
    color: C.muted,
    fontSize: '0.85rem',
    marginTop: 4,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  label: {
    color: C.muted,
    fontSize: '0.8rem',
    fontWeight: 500,
    marginBottom: 2,
  },
  input: {
    background: '#0d1e2d',
    border: `1px solid ${C.border}`,
    borderRadius: 8,
    color: C.text,
    padding: '10px 14px',
    fontSize: '0.9rem',
    outline: 'none',
    width: '100%',
  },
  error: {
    color: C.error,
    fontSize: '0.8rem',
    padding: '8px 12px',
    background: 'rgba(255,82,82,0.1)',
    border: '1px solid rgba(255,82,82,0.3)',
    borderRadius: 6,
  },
  btn: {
    background: C.cyan,
    color: '#0F1923',
    border: 'none',
    borderRadius: 8,
    padding: '11px 0',
    fontWeight: 700,
    fontSize: '0.9rem',
    cursor: 'pointer',
    marginTop: 4,
  },
  demoSection: {
    marginTop: 24,
    borderTop: `1px solid ${C.border}`,
    paddingTop: 20,
  },
  demoTitle: {
    color: C.muted,
    fontSize: '0.75rem',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  demoBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: 2,
    width: '100%',
    background: 'transparent',
    border: `1px solid ${C.border}`,
    borderRadius: 6,
    padding: '8px 12px',
    marginBottom: 6,
    cursor: 'pointer',
    textAlign: 'left',
  },
}
