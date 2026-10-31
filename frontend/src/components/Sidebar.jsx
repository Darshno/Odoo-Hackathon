import { BarChart3, CreditCard, FileText, LogOut, Menu, Package, Repeat2, Settings, Users, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import Logo from './Logo'
import { useAuth } from '../hooks/AuthContext'

export default function Sidebar() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)

  const isCustomer = user?.role === 'CUSTOMER'
  const links = isCustomer
    ? [
        { to: '/my-quotations', label: 'My Quotations', icon: FileText },
        { to: '/plans', label: 'My Plans', icon: Repeat2 },
        { to: '/subscriptions', label: 'Subscriptions', icon: CreditCard },
        { to: '/profile', label: 'Profile', icon: Settings },
      ]
    : [
        { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
        { to: '/products', label: 'Products', icon: Package },
        { to: '/plans', label: 'Plans', icon: Repeat2 },
        { to: '/subscriptions', label: 'Subscriptions', icon: CreditCard },
        ...(user?.role === 'ADMIN' ? [{ to: '/admin/users', label: 'User Management', icon: Users }] : []),
        { to: '/profile', label: 'Profile', icon: Settings },
      ]

  return <>
    <button className="mobile-sidebar-toggle" onClick={() => setOpen(true)} aria-label="Open dashboard navigation"><Menu /></button>
    <aside className={`dashboard-sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-top"><Logo /><button className="icon-button mobile-only" onClick={() => setOpen(false)} aria-label="Close dashboard navigation"><X /></button></div>
      <nav className="sidebar-nav">
        <span className="sidebar-eyebrow">Workspace</span>
        {links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}><Icon size={17} /><span>{label}</span></NavLink>)}
      </nav>
      <div className="sidebar-bottom"><div className="sidebar-user"><span className="avatar">{user?.full_name?.charAt(0)}</span><div><strong>{user?.full_name}</strong><span>{user?.role}</span></div></div><button className="sidebar-logout" onClick={logout}><LogOut size={16} /> Sign out</button></div>
    </aside>
    {open && <button className="sidebar-backdrop" onClick={() => setOpen(false)} aria-label="Close navigation" />}
  </>
}
