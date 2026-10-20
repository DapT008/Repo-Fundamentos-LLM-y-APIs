import { useState, useEffect } from 'react'
import { getAuditLogs, verifyIntegrity } from '../lib/api.js'
import { ClipboardList, CheckCircle, XCircle, RefreshCw, ShieldCheck } from 'lucide-react'

const C = {
  bg: '#0F1923', panel: '#1A2838', panel2: '#223548',
  cyan: '#00D4FF', green: '#00E676', gold: '#F5A623',
  error: '#ff5252', text: '#E0E8F0', muted: '#7A95AA', border: '#2a3f54',
}

const EVENT_COLORS = {
  AUTH_SUCCESS: C.green, AUTH_FAILURE: C.error, CHAT_REQUEST: C.cyan,
  WAF_BLOCK: C.gold, ADMIN_ACCESS: C.gold, RATE_LIMIT: C.error,
}

export default function AuditPage() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [integrity, setIntegrity] = useState(null)
  const [integrityLoading, setIntegrityLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchLogs = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getAuditLogs()
      setLogs(data.logs || data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error cargando logs (¿tienes scope admin?)')
    } finally {
      setLoading(false)
    }
  }

  const checkIntegrity = async () => {
    setIntegrityLoading(true)
    try {
      const data = await verifyIntegrity()
      setIntegrity(data)
    } catch (err) {
      setIntegrity({ valid: false, error: err.response?.data?.detail || 'Error' })
    } finally {
      setIntegrityLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, [])

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <ClipboardList size={20} color={C.cyan} />
        <span style={{ marginLeft: 8, fontWeight: 600 }}>Audit Log</span>
        <span style={styles.adminBadge}>admin</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button onClick={checkIntegrity} disabled={integrityLoading} style={styles.actionBtn}>
            <ShieldCheck size={14} style={{ marginRight: 4 }} />
            {integrityLoading ? 'Verificando...' : 'Verificar Integridad'}
          </button>
          <button onClick={fetchLogs} disabled={loading} style={styles.actionBtn}>
            <RefreshCw size={14} style={{ marginRight: 4 }} />
            Actualizar
          </button>
        </div>
      </div>

      {/* Integrity banner */}
      {integrity && (
        <div style={{
          ...styles.integrityBanner,
          background: integrity.valid ? 'rgba(0,230,118,0.08)' : 'rgba(255,82,82,0.08)',
          borderColor: integrity.valid ? 'rgba(0,230,118,0.25)' : 'rgba(255,82,82,0.25)',
        }}>
          {integrity.valid
            ? <CheckCircle size={16} color={C.green} style={{ marginRight: 8 }} />
            : <XCircle size={16} color={C.error} style={{ marginRight: 8 }} />}
          <span style={{ color: integrity.valid ? C.green : C.error, fontWeight: 600 }}>
            {integrity.valid
              ? `Cadena íntegra · ${integrity.total_entries} entradas verificadas`
              : `Integridad comprometida: ${integrity.error || 'hash mismatch'}`}
          </span>
        </div>
      )}

      <div style={styles.content}>
        {error ? (
          <div style={styles.errBox}>{error}</div>
        ) : loading ? (
          <div style={styles.center}>Cargando logs...</div>
        ) : logs.length === 0 ? (
          <div style={styles.center}>No hay entradas en el log</div>
        ) : (
          <div style={styles.table}>
            <div style={styles.tableHeader}>
              <span style={{ flex: '0 0 180px' }}>Timestamp</span>
              <span style={{ flex: '0 0 160px' }}>Evento</span>
              <span style={{ flex: '0 0 200px' }}>Usuario</span>
              <span style={{ flex: 1 }}>Detalles</span>
              <span style={{ flex: '0 0 90px', textAlign: 'right' }}>Hash</span>
            </div>
            {logs.map((log, i) => (
              <LogRow key={i} log={log} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function LogRow({ log }) {
  const [expanded, setExpanded] = useState(false)
  const eventColor = EVENT_COLORS[log.event] || C.muted

  return (
    <div
      onClick={() => setExpanded(v => !v)}
      style={{ ...styles.row, cursor: 'pointer' }}
    >
      <div style={styles.rowMain}>
        <span style={{ flex: '0 0 180px', color: C.muted, fontSize: '0.75rem', fontFamily: 'monospace' }}>
          {new Date(log.timestamp).toLocaleString()}
        </span>
        <span style={{ flex: '0 0 160px' }}>
          <span style={{ ...styles.eventBadge, color: eventColor, borderColor: eventColor + '40', background: eventColor + '12' }}>
            {log.event}
          </span>
        </span>
        <span style={{ flex: '0 0 200px', color: C.text, fontSize: '0.8rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {log.user_id || '—'}
        </span>
        <span style={{ flex: 1, color: C.muted, fontSize: '0.8rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {log.details ? JSON.stringify(log.details).substring(0, 60) : '—'}
        </span>
        <span style={{ flex: '0 0 90px', textAlign: 'right', fontFamily: 'monospace', fontSize: '0.7rem', color: '#4a6580' }}>
          {log.hash?.substring(0, 8)}…
        </span>
      </div>
      {expanded && log.details && (
        <div style={styles.expanded}>
          <pre style={{ margin: 0, color: C.muted, fontSize: '0.75rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {JSON.stringify(log.details, null, 2)}
          </pre>
          {log.prev_hash && (
            <div style={{ marginTop: 8, fontSize: '0.7rem', color: '#4a6580' }}>
              <span style={{ color: C.muted }}>prev_hash: </span>{log.prev_hash.substring(0, 16)}…
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const styles = {
  root: { display: 'flex', flexDirection: 'column', height: '100%', background: C.bg },
  header: {
    display: 'flex', alignItems: 'center',
    padding: '14px 20px',
    borderBottom: `1px solid ${C.border}`,
    background: C.panel, color: C.text,
    fontWeight: 500, flexShrink: 0, gap: 8,
  },
  adminBadge: {
    fontSize: '0.65rem', color: C.gold,
    background: 'rgba(245,166,35,0.12)',
    border: '1px solid rgba(245,166,35,0.3)',
    padding: '2px 6px', borderRadius: 4,
  },
  actionBtn: {
    display: 'flex', alignItems: 'center',
    background: 'transparent', border: `1px solid ${C.border}`,
    color: C.muted, padding: '5px 12px', borderRadius: 6,
    cursor: 'pointer', fontSize: '0.8rem',
  },
  integrityBanner: {
    display: 'flex', alignItems: 'center',
    padding: '10px 20px',
    borderBottom: `1px solid`,
    flexShrink: 0, fontSize: '0.85rem',
  },
  content: { flex: 1, overflow: 'auto' },
  table: { width: '100%' },
  tableHeader: {
    display: 'flex', padding: '10px 20px',
    fontSize: '0.7rem', color: C.muted,
    textTransform: 'uppercase', letterSpacing: '0.06em',
    borderBottom: `1px solid ${C.border}`,
    background: C.panel,
    position: 'sticky', top: 0, zIndex: 1,
  },
  row: {
    borderBottom: `1px solid ${C.border}`,
    transition: 'background 0.1s',
  },
  rowMain: {
    display: 'flex', alignItems: 'center',
    padding: '10px 20px',
  },
  eventBadge: {
    fontSize: '0.7rem', fontWeight: 600,
    padding: '2px 6px', borderRadius: 4,
    border: '1px solid', display: 'inline-block',
  },
  expanded: {
    padding: '8px 20px 12px 380px',
    background: C.panel2,
    borderTop: `1px solid ${C.border}`,
  },
  errBox: {
    margin: 20, padding: '12px 16px',
    background: 'rgba(255,82,82,0.08)',
    border: '1px solid rgba(255,82,82,0.2)',
    borderRadius: 8, color: C.error, fontSize: '0.875rem',
  },
  center: {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    height: 200, color: C.muted, fontSize: '0.9rem',
  },
}
