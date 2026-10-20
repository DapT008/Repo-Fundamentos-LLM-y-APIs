import { useState, useEffect } from 'react'
import { getHealth, getCircuit } from '../lib/api.js'
import { RefreshCw, CheckCircle, AlertTriangle, XCircle, Activity } from 'lucide-react'

const C = {
  bg: '#0F1923',
  panel: '#1A2838',
  panel2: '#223548',
  cyan: '#00D4FF',
  green: '#00E676',
  gold: '#F5A623',
  error: '#ff5252',
  text: '#E0E8F0',
  muted: '#7A95AA',
  border: '#2a3f54',
}

export default function HealthPage() {
  const [health, setHealth] = useState(null)
  const [circuit, setCircuit] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    try {
      const [h, c] = await Promise.all([getHealth(), getCircuit()])
      setHealth(h)
      setCircuit(c)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 15_000)
    return () => clearInterval(id)
  }, [])

  const statusIcon = (s) => {
    if (s === 'healthy') return <CheckCircle size={16} color={C.green} />
    if (s === 'degraded') return <AlertTriangle size={16} color={C.gold} />
    return <XCircle size={16} color={C.error} />
  }

  const statusColor = (s) => {
    if (s === 'healthy') return C.green
    if (s === 'degraded') return C.gold
    return C.error
  }

  const cbColor = (state) => {
    if (state === 'CERRADO') return C.green
    if (state === 'SEMIABIERTO') return C.gold
    return C.error
  }

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <Activity size={20} color={C.cyan} />
        <span style={{ marginLeft: 8, fontWeight: 600 }}>Health Monitor</span>
        <button onClick={refresh} disabled={loading} style={styles.refreshBtn}>
          <RefreshCw size={14} style={{ marginRight: 4 }} />
          Actualizar
        </button>
      </div>

      {loading && !health ? (
        <div style={styles.empty}>Cargando...</div>
      ) : health ? (
        <div style={styles.content}>
          {/* Status general */}
          <Card title="Estado General">
            <StatRow label="Estado" value={
              <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: statusColor(health.status) }}>
                {statusIcon(health.status)}
                {health.status?.toUpperCase()}
              </span>
            } />
            <StatRow label="Uptime" value={`${Math.floor((health.uptime_seconds || 0) / 60)} min`} />
            <StatRow label="Versión" value={health.version || '—'} />
            <StatRow label="Timestamp" value={new Date(health.timestamp).toLocaleTimeString()} />
          </Card>

          {/* Ollama */}
          <Card title="Ollama LLM">
            <StatRow label="Estado" value={
              <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: statusColor(health.ollama?.status) }}>
                {statusIcon(health.ollama?.status)}
                {health.ollama?.status?.toUpperCase() || '—'}
              </span>
            } />
            <StatRow label="Latencia" value={health.ollama?.latency_ms ? `${health.ollama.latency_ms} ms` : '—'} />
            <StatRow label="Modelos" value={health.ollama?.models?.join(', ') || '—'} />
          </Card>

          {/* Circuit Breaker */}
          {circuit && (
            <Card title="Circuit Breaker">
              <StatRow label="Estado" value={
                <span style={{ fontWeight: 700, color: cbColor(circuit.state) }}>
                  {circuit.state === 'CERRADO' ? '🟢' : circuit.state === 'SEMIABIERTO' ? '🟡' : '🔴'} {circuit.state}
                </span>
              } />
              <StatRow label="Fallos consecutivos" value={circuit.failures || 0} />
              <StatRow label="Umbral de apertura" value={circuit.threshold || '—'} />
              <StatRow label="Timeout recuperación" value={circuit.recovery_timeout ? `${circuit.recovery_timeout}s` : '—'} />
            </Card>
          )}

          {/* Disco */}
          {health.disk && (
            <Card title="Almacenamiento">
              <StatRow label="Total" value={`${health.disk.total_gb?.toFixed(1)} GB`} />
              <StatRow label="Libre" value={`${health.disk.free_gb?.toFixed(1)} GB`} />
              <StatRow label="Usado" value={`${health.disk.used_pct?.toFixed(0)}%`} />
            </Card>
          )}
        </div>
      ) : (
        <div style={styles.empty}>No se pudo conectar al backend</div>
      )}
    </div>
  )
}

function Card({ title, children }) {
  return (
    <div style={{
      background: C.panel,
      border: `1px solid ${C.border}`,
      borderRadius: 10,
      padding: 20,
    }}>
      <h3 style={{ color: C.cyan, fontSize: '0.85rem', textTransform: 'uppercase',
        letterSpacing: '0.07em', marginBottom: 14 }}>{title}</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>{children}</div>
    </div>
  )
}

function StatRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontSize: '0.875rem' }}>
      <span style={{ color: C.muted }}>{label}</span>
      <span style={{ color: C.text, fontWeight: 500 }}>{value}</span>
    </div>
  )
}

const styles = {
  root: { display: 'flex', flexDirection: 'column', height: '100%', background: C.bg },
  header: {
    display: 'flex', alignItems: 'center',
    padding: '14px 20px',
    borderBottom: `1px solid ${C.border}`,
    background: C.panel,
    color: C.text, fontWeight: 500, flexShrink: 0,
  },
  refreshBtn: {
    marginLeft: 'auto',
    display: 'flex', alignItems: 'center',
    background: 'transparent', border: `1px solid ${C.border}`,
    color: C.muted, padding: '5px 12px', borderRadius: 6,
    cursor: 'pointer', fontSize: '0.8rem',
  },
  content: {
    flex: 1, overflow: 'auto',
    padding: 20,
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 16,
    alignContent: 'start',
  },
  empty: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: C.muted, fontSize: '0.9rem',
  },
}
