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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('hira-token')
  if (!token) return <Navigate to="/login" replace />
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
          <Route path="config" element={<ConfigPage />} />
          <Route path="config/:section" element={<ConfigPage />} />
          <Route path="logic" element={<LogicPage />} />
          <Route path="ai" element={<AIChatPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
