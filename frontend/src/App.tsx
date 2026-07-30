import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Shell from './components/layout/Shell'
import LoginPage from './components/auth/LoginPage'
import { DashboardPage } from './components/dashboard/DashboardPage'
import { AlarmsPage } from './components/alarms/AlarmsPage'
import HistoryPage from './components/historicals/HistoryPage'
import ConfigPage from './components/config/ConfigPage'
import LogicPage from './components/logic/LogicPage'
import { AIChatPage } from './components/ai/AIChatPage'
import { ClientAIChatPage } from './components/ai/ClientAIChatPage'
import SystemStatusPage from './pages/SystemStatusPage'
import NotificationsConfigPage from './pages/NotificationsConfigPage'
import TestsPage from './pages/TestsPage'
import AnalysisPage from './pages/AnalysisPage'
import DocumentationPage from './pages/DocumentationPage'
import { useAuthStore } from './store/authStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('hira-token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('hira-token')
  if (!token) return <Navigate to="/login" replace />
  const isAdmin = useAuthStore.getState().isAdmin()
  if (!isAdmin) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function OperadorRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('hira-token')
  if (!token) return <Navigate to="/login" replace />
  const isOperador = useAuthStore.getState().isOperador()
  if (!isOperador) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  useEffect(() => {
    const stored = localStorage.getItem('hira-theme')
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const theme = stored ?? (systemDark ? 'dark' : 'light')
    document.documentElement.setAttribute('data-theme', theme)
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Shell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="alarms" element={<AlarmsPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="config" element={<AdminRoute><ConfigPage /></AdminRoute>} />
          <Route path="config/:section" element={<AdminRoute><ConfigPage /></AdminRoute>} />
          <Route path="logic" element={<AdminRoute><LogicPage /></AdminRoute>} />
          <Route path="ai/integrador" element={<AdminRoute><AIChatPage /></AdminRoute>} />
          <Route path="ai/cliente" element={<OperadorRoute><ClientAIChatPage /></OperadorRoute>} />
          {/* Compat: /ai redirige a /ai/integrador (Admin) o /ai/cliente (Operador) */}
          <Route path="ai" element={<Navigate to="/ai/integrador" replace />} />
          <Route path="system/status" element={<OperadorRoute><SystemStatusPage /></OperadorRoute>} />
          <Route path="studio/notifications" element={<AdminRoute><NotificationsConfigPage /></AdminRoute>} />
          <Route path="tests" element={<AdminRoute><TestsPage /></AdminRoute>} />
          <Route path="analysis" element={<OperadorRoute><AnalysisPage /></OperadorRoute>} />
          <Route path="docs" element={<AdminRoute><DocumentationPage /></AdminRoute>} />
          <Route path="manual" element={<OperadorRoute><DocumentationPage readonly /></OperadorRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
