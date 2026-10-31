import { ArrowUpRight, CircleDollarSign, Clock3, ShieldCheck, UsersRound } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/AuthContext'
import { listUsers } from '../services/auth'
import { getRevenueAnalytics } from '../services/billing'
import { DashboardCard, PageHeader } from '../components/DashboardPrimitives'
import { StatusBadge } from '../components/FormControls'
import { errorMessage } from '../utils/validation'

function dateInputValue(value) {
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatAmount(currency, amount) {
  const locale = currency === 'INR' ? 'en-IN' : 'en-US'
  const numericAmount = Number(amount)
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(numericAmount)
  } catch (error) {
    if (!(error instanceof RangeError)) throw error
    return `${currency} ${numericAmount.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
}

function formatTotals(items) {
  return items?.length
    ? items.map(({ currency, amount }) => formatAmount(currency, amount)).join(' · ')
    : '—'
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [userCount, setUserCount] = useState(null)
  const today = new Date()
  const [dateTo, setDateTo] = useState(dateInputValue(today))
  const [dateFrom, setDateFrom] = useState(dateInputValue(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 29)))
  const [analytics, setAnalytics] = useState(null)
  const [analyticsError, setAnalyticsError] = useState('')

  useEffect(() => {
    if (user?.role === 'ADMIN') {
      listUsers({ page: 1, page_size: 1 })
        .then(({ data }) => setUserCount(data.total))
        .catch(() => setUserCount(null))
    }
  }, [user?.role])

  useEffect(() => {
    let active = true
    getRevenueAnalytics({ date_from: dateFrom, date_to: dateTo })
      .then(({ data }) => {
        if (active) {
          setAnalytics(data)
          setAnalyticsError('')
        }
      })
      .catch((error) => {
        if (active) setAnalyticsError(errorMessage(error))
      })
    return () => { active = false }
  }, [dateFrom, dateTo])

  if (user?.role !== 'ADMIN' && user?.role !== 'STAFF') return <Navigate to="/my-quotations" replace />

  const isAdmin = user?.role === 'ADMIN'
  const subscriptions = analytics?.subscriptions
  return <section className="dashboard-page content-wrap">
    <PageHeader
      eyebrow={`${user?.role} workspace`}
      title={`Good to see you, ${user?.full_name?.split(' ')[0]}.`}
      description="Track revenue, outstanding invoices, and subscription activity."
      actions={<div className="analytics-date-filter">
        <label>From<input type="date" value={dateFrom} max={dateTo} onChange={(event) => setDateFrom(event.target.value)} /></label>
        <label>To<input type="date" value={dateTo} min={dateFrom} onChange={(event) => setDateTo(event.target.value)} /></label>
      </div>}
    />
    {analyticsError && <p className="form-error" role="alert">{analyticsError}</p>}
    <div className="dashboard-grid analytics-grid">
      {isAdmin && <DashboardCard label="Registered users" value={userCount ?? '—'} detail="From the live API" icon={UsersRound} />}
      <DashboardCard label="Paid revenue" value={formatTotals(analytics?.paid_revenue)} detail="Confirmed payments in selected dates" icon={CircleDollarSign} />
      <DashboardCard label="Outstanding balance" value={formatTotals(analytics?.outstanding_balance)} detail="Current issued invoice balances" icon={Clock3} />
      <DashboardCard label="Active subscriptions" value={subscriptions?.active ?? '—'} detail={`${subscriptions?.paused ?? '—'} paused · ${subscriptions?.closed ?? '—'} closed`} icon={ShieldCheck} />
      <div className="dashboard-card analytics-activity">
        <div className="analytics-section-heading"><div><span className="card-label">Recent payment activity</span><p>Latest confirmed payments in the selected date range</p></div><Link className="inline-link" to="/invoices">View invoices <ArrowUpRight size={15} /></Link></div>
        {analytics?.recent_payments?.length
          ? <div className="analytics-payment-list">{analytics.recent_payments.map((payment) => <div className="analytics-payment-row" key={payment.id}>
            <div><strong>{payment.customer_name}</strong><span>{payment.payment_number} · {new Date(payment.received_at).toLocaleDateString()}</span></div>
            <strong>{formatAmount(payment.currency, payment.amount)}</strong>
          </div>)}</div>
          : <p className="analytics-empty">{analytics ? 'No confirmed payments in this date range.' : 'Loading analytics…'}</p>}
      </div>
      <div className="dashboard-card dashboard-card-wide"><span className="card-label">Profile snapshot</span><div className="profile-snapshot"><div><strong>{user?.full_name}</strong><span>{user?.email}</span></div><StatusBadge active={user?.is_active}>{user?.is_active ? 'Active account' : 'Inactive account'}</StatusBadge></div><Link className="inline-link" to="/profile">Review profile <ArrowUpRight size={15} /></Link></div>
    </div>
    {isAdmin && <div className="dashboard-callout"><div><span className="eyebrow">Admin focus</span><h2>Keep the workspace orderly.</h2><p>Manage access and staff accounts without leaving the calm Brightloop rhythm.</p></div><Link className="button button-dark" to="/admin/users">Open user management <ArrowUpRight size={16} /></Link></div>}
  </section>
}
