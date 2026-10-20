import { NavLink } from 'react-router-dom'
import { MessageSquare, Activity, Shield, ClipboardList, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth.js'

const C = {
  bg: '#0F1923',
  panel: '#1A2838',
  panel2: '#223548',
  cyan: '#00D4FF',
  gold: '#F5A623',
  green: '#00E676',
  text: '#E0E8F0',
  muted: '#7A95AA',
  border: '#2a3f54',
}

const navItems = [
  { to: '/chat',     icon: MessageSquare, label: 'Chat' },
  { to: '/health',   icon: Activity,      label: 'Health' },
  { to: '/security', icon: Shield,        label: 'WAF Scan' },
  { to: '/audit',    icon: ClipboardList, label: 'Audit Log', adminOnly: true },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const isAdmin = user?.scopes?.includes('admin')

  return (
    <div style={styles.root}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.logo}>
          <span style={{ color: C.cyan, fontWeight: 700, fontSize: '1.1rem' }}>
            🔐 LLM Lab
          </span>
          <span style={{ color: C.muted, fontSize: '0.7rem', display: 'block', marginTop: 2 }}>
            Sesión 3 · Seguridad
          </span>
        </div>

        <nav style={styles.nav}>
          {navItems
            .filter(item => !item.adminOnly || isAdmin)
            .map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                style={({ isActive }) => ({
                  ...styles.navLink,
                  background: isActive ? C.panel2 : 'transparent',
                  color: isActive ? C.cyan : C.text,
                  borderLeft: isActive ? `3px solid ${C.cyan}` : '3px solid transparent',
                })}
              >
                <Icon size={16} style={{ marginRight: 8, flexShrink: 0 }} />
                {label}
              </NavLink>
            ))}
        </nav>

        <div style={styles.userInfo}>
          <div style={{ fontSize: '0.75rem', color: C.muted, marginBottom: 4 }}>
            {user?.email}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
            {user?.scopes?.map(s => (
              <span key={s} style={styles.scope}>{s}</span>
            ))}
          </div>
          <button onClick={logout} style={styles.logoutBtn}>
            <LogOut size={14} style={{ marginRight: 4 }} />
            Salir
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={styles.main}>
        {children}
      </main>
    </div>
  )
}

const styles = {
  root: {
    display: 'flex',
    height: '100vh',
    background: C.bg,
    overflow: 'hidden',
  },
  sidebar: {
    width: 220,
    background: C.panel,
    borderRight: `1px solid ${C.border}`,
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
  },
  logo: {
    padding: '20px 16px 16px',
    borderBottom: `1px solid ${C.border}`,
  },
  nav: {
    flex: 1,
    padding: '12px 0',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  navLink: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 16px',
    textDecoration: 'none',
    fontSize: '0.875rem',
    fontWeight: 500,
    transition: 'background 0.15s, color 0.15s',
    borderRadius: '0 6px 6px 0',
    marginRight: 8,
  },
  userInfo: {
    padding: '12px 16px',
    borderTop: `1px solid ${C.border}`,
  },
  scope: {
    background: '#0d2235',
    color: C.cyan,
    fontSize: '0.65rem',
    padding: '2px 6px',
    borderRadius: 4,
    border: `1px solid #1a3a55`,
  },
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    background: 'transparent',
    border: `1px solid ${C.border}`,
    color: C.muted,
    padding: '6px 10px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: '0.8rem',
    width: '100%',
    justifyContent: 'center',
  },
  main: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
  },
}
