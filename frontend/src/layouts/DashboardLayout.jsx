import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'

export default function DashboardLayout() {
  return <div className="dashboard-shell"><Sidebar /><div className="dashboard-main"><Outlet /></div></div>
}
