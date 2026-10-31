import { ArrowUpRight, ShieldCheck, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/AuthContext'
import { listUsers } from '../services/auth'
import { DashboardCard, PageHeader } from '../components/DashboardPrimitives'
import { StatusBadge } from '../components/FormControls'

export default function DashboardPage() {
  const { user } = useAuth()
  const [userCount, setUserCount] = useState(null)
  useEffect(() => { if (user?.role === 'ADMIN') listUsers({ page: 1, page_size: 1 }).then(({ data }) => setUserCount(data.total)).catch(() => setUserCount(null)) }, [user?.role])
  const isAdmin = user?.role === 'ADMIN'
  return <section className="dashboard-page content-wrap"><PageHeader eyebrow={`${user?.role} workspace`} title={`Good to see you, ${user?.full_name?.split(' ')[0]}.`} description={isAdmin ? 'A concise view of your Brightloop foundation.' : 'Your Brightloop workspace is ready for the next step.'} />
    <div className="dashboard-grid">{isAdmin ? <DashboardCard label="Registered users" value={userCount ?? '—'} detail="From the live API" icon={UsersRound} /> : <DashboardCard label="Account status" value={user?.is_active ? 'Active' : 'Inactive'} detail="Your access is current" icon={ShieldCheck} />}<div className="dashboard-card dashboard-card-wide"><span className="card-label">Profile snapshot</span><div className="profile-snapshot"><div><strong>{user?.full_name}</strong><span>{user?.email}</span></div><StatusBadge active={user?.is_active}>{user?.is_active ? 'Active account' : 'Inactive account'}</StatusBadge></div><Link className="inline-link" to="/profile">Review profile <ArrowUpRight size={15} /></Link></div></div>
    {isAdmin && <div className="dashboard-callout"><div><span className="eyebrow">Admin focus</span><h2>Keep the workspace orderly.</h2><p>Manage access and staff accounts without leaving the calm Brightloop rhythm.</p></div><Link className="button button-dark" to="/admin/users">Open user management <ArrowUpRight size={16} /></Link></div>}
    {!isAdmin && <div className="dashboard-callout"><div><span className="eyebrow">Phase 1 foundation</span><h2>Subscription features are coming later.</h2><p>Products, plans, invoices, payments, and analytics are planned for the next development phase. Your account and profile foundation are ready today.</p></div></div>}
  </section>
}
