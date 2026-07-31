import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import EngineeringSessionBanner from '../EngineeringSessionBanner'

export default function Shell() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <main style={{
        flex: 1,
        overflow: 'auto',
        background: 'var(--bg-base)',
        color: 'var(--text-primary)',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <EngineeringSessionBanner />
        <div style={{ flex: 1, padding: '24px 28px' }}>
          <Outlet />
        </div>
      </main>
    </div>
  )
}
