import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.js'
import LoginPage from './pages/LoginPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import HealthPage from './pages/HealthPage.jsx'
import AuditPage from './pages/AuditPage.jsx'
import SecurityPage from './pages/SecurityPage.jsx'
import Layout from './components/Layout.jsx'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div style={styles.loading}>Cargando...</div>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Navigate to="/chat" replace />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/health" element={<HealthPage />} />
                  <Route path="/audit" element={<AuditPage />} />
                  <Route path="/security" element={<SecurityPage />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </AuthProvider>
  )
}

const styles = {
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    color: '#00D4FF',
    background: '#0F1923',
    fontSize: '1.2rem',
  },
}
