import { CalendarRange, CreditCard, RefreshCcw, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, PrimaryButton } from '../components/FormControls'
import { PageHeader } from '../components/DashboardPrimitives'
import { useAuth } from '../hooks/AuthContext'
import { listUsers } from '../services/auth'
import { listSubscriptions, processDueSubscriptions, activateSubscription, pauseSubscription, resumeSubscription, renewSubscription, closeSubscription } from '../services/subscriptions'
import { errorMessage } from '../utils/validation'

const statusLabels = {
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  CLOSED: 'Closed',
}

const statusClasses = {
  ACTIVE: 'status-accepted',
  PAUSED: 'status-sent',
  CLOSED: 'status-cancelled',
}

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date)
}

const formatCurrency = (currency, value) => {
  const code = currency || 'USD'
  const numeric = Number(value ?? 0)
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: code }).format(numeric)
}

export default function SubscriptionsPage() {
  const { user } = useAuth()
  const isAdminStaff = ['ADMIN', 'STAFF'].includes(user?.role)
  const [items, setItems] = useState([])
  const [customers, setCustomers] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [pages, setPages] = useState(0)
  const [total, setTotal] = useState(0)
  const [searchInput, setSearchInput] = useState('')
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    customer_id: '',
    start_date_from: '',
    start_date_to: '',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [processing, setProcessing] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)

  const load = async (nextPage = page) => {
    setLoading(true)
    setError('')
    try {
      const params = {
        page: nextPage,
        page_size: pageSize,
        search: filters.search || undefined,
        status: filters.status || undefined,
        customer_id: filters.customer_id || undefined,
        start_date_from: filters.start_date_from || undefined,
        start_date_to: filters.start_date_to || undefined,
      }
      const { data } = await listSubscriptions(params)
      setItems(data.items || [])
      setPages(data.pages || 0)
      setTotal(data.total || 0)
    } catch (err) {
      setError(errorMessage(err, 'We could not load subscriptions.'))
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdminStaff) return
    listUsers({ page: 1, page_size: 200, role: 'CUSTOMER' })
      .then(({ data }) => setCustomers(data.items || []))
      .catch(() => setCustomers([]))
  }, [isAdminStaff])

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((current) => ({ ...current, search: searchInput.trim() }))
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    load(page)
  }, [page, filters.search, filters.status, filters.customer_id, filters.start_date_from, filters.start_date_to])

  const handleProcessDue = async () => {
    const confirmed = window.confirm('This will process any overdue subscriptions manually. Continue?')
    if (!confirmed) return

    setProcessing(true)
    setError('')
    setNotice('')
    try {
      const { data } = await processDueSubscriptions()
      setNotice(`${data.processed ?? 0} subscription${data.processed === 1 ? '' : 's'} processed.`)
      await load(page)
    } catch (err) {
      setError(errorMessage(err, 'We could not process due subscriptions.'))
    } finally {
      setProcessing(false)
    }
  }

  const handleLifecycleAction = async (subscription, action) => {
    const labelMap = {
      activate: 'activate',
      pause: 'pause',
      resume: 'resume',
      renew: 'renew',
      close: 'close',
    }

    const shouldConfirm = action === 'close'
    if (shouldConfirm) {
      const confirmed = window.confirm(`Close subscription ${subscription.subscription_number}? This action cannot be undone.`)
      if (!confirmed) return
    }

    setPendingAction(`${subscription.id}:${action}`)
    setError('')
    setNotice('')
    try {
      if (action === 'activate') await activateSubscription(subscription.id)
      if (action === 'pause') await pauseSubscription(subscription.id)
      if (action === 'resume') await resumeSubscription(subscription.id)
      if (action === 'renew') await renewSubscription(subscription.id)
      if (action === 'close') await closeSubscription(subscription.id)
      setNotice(`Subscription ${subscription.subscription_number} was ${labelMap[action]}.`)
      await load(page)
    } catch (err) {
      setError(errorMessage(err, `We could not ${labelMap[action]} this subscription.`))
    } finally {
      setPendingAction(null)
    }
  }

  const customerFilter = useMemo(() => {
    if (!isAdminStaff) return null
    return (
      <label className="subscription-filter-item">
        <span>Customer</span>
        <select value={filters.customer_id} onChange={(event) => {
          setFilters((current) => ({ ...current, customer_id: event.target.value }))
          setPage(1)
        }}>
          <option value="">All customers</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>{customer.full_name}</option>
          ))}
        </select>
      </label>
    )
  }, [customers, filters.customer_id, isAdminStaff])

  const renderActions = (subscription) => {
    if (!isAdminStaff) return <Link to={`/subscriptions/${subscription.id}`} className="table-text-link">View</Link>

    const canPause = subscription.lines?.length > 0 && subscription.lines.every((line) => line.pause_allowed)
    const canRenew = subscription.lines?.length > 0 && subscription.lines.every((line) => line.renewal_allowed)

    const buttons = []
    if (subscription.status === 'ACTIVE') {
      if (canPause) buttons.push({ key: 'pause', label: 'Pause' })
      if (canRenew) buttons.push({ key: 'renew', label: 'Renew' })
      buttons.push({ key: 'close', label: 'Close' })
    }
    if (subscription.status === 'PAUSED') {
      buttons.push({ key: 'activate', label: 'Activate' })
      buttons.push({ key: 'resume', label: 'Resume' })
      buttons.push({ key: 'close', label: 'Close' })
    }
    if (subscription.status === 'CLOSED') {
      return <Link to={`/subscriptions/${subscription.id}`} className="table-text-link">View</Link>
    }

    return (
      <div className="table-actions-row">
        <Link to={`/subscriptions/${subscription.id}`} className="table-text-link">View</Link>
        {buttons.map((button) => (
          <button
            key={button.key}
            className="mini-button subtle"
            disabled={pendingAction === `${subscription.id}:${button.key}`}
            onClick={() => handleLifecycleAction(subscription, button.key)}
          >
            {button.label}
          </button>
        ))}
      </div>
    )
  }

  return (
    <section className="dashboard-page content-wrap">
      <PageHeader
        eyebrow={isAdminStaff ? 'Subscription management' : 'Customer workspace'}
        title="Subscriptions"
        description={
          isAdminStaff
            ? 'Track customer subscriptions, running cycles, and lifecycle status across the platform.'
            : 'Review your subscription commitments, billing schedule, and current status.'
        }
        actions={
          isAdminStaff && (
            <PrimaryButton onClick={handleProcessDue} loading={processing}>
              <CreditCard size={16} /> Process due subscriptions
            </PrimaryButton>
          )
        }
      />

      <Alert type="success">{notice}</Alert>
      <Alert>{error}</Alert>

      <div className="table-card subscription-table-card">
        <div className="table-toolbar subscription-toolbar">
          <label className="search-box" aria-label="Search subscriptions">
            <Search size={16} />
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search by number, customer, or email"
            />
          </label>

          <label className="subscription-filter-item">
            <span>Status</span>
            <select
              value={filters.status}
              onChange={(event) => {
                setFilters((current) => ({ ...current, status: event.target.value }))
                setPage(1)
              }}
            >
              <option value="">All statuses</option>
              {Object.entries(statusLabels).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </label>

          {customerFilter}

          <label className="subscription-filter-item">
            <span>From</span>
            <input
              type="date"
              value={filters.start_date_from}
              onChange={(event) => {
                setFilters((current) => ({ ...current, start_date_from: event.target.value }))
                setPage(1)
              }}
            />
          </label>

          <label className="subscription-filter-item">
            <span>To</span>
            <input
              type="date"
              value={filters.start_date_to}
              onChange={(event) => {
                setFilters((current) => ({ ...current, start_date_to: event.target.value }))
                setPage(1)
              }}
            />
          </label>

          <button className="button button-secondary refresh-button" type="button" onClick={() => load(page)}>
            <RefreshCcw size={15} /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="table-empty">Loading subscriptions…</div>
        ) : items.length === 0 ? (
          <div className="table-empty">No subscriptions match the current filters.</div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Subscription</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Cycle</th>
                  <th>Next billing</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((subscription) => (
                  <tr key={subscription.id}>
                    <td>
                      <Link to={`/subscriptions/${subscription.id}`} className="table-name-button">
                        <strong>{subscription.subscription_number}</strong>
                        <span className="cell-sub">Start {formatDate(subscription.start_date)}</span>
                      </Link>
                    </td>
                    <td>
                      <div className="cell-stack">
                        <strong>{subscription.customer?.full_name || '—'}</strong>
                        <span className="cell-sub">{subscription.customer?.email || '—'}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`status-pill ${statusClasses[subscription.status] || 'status-draft'}`}>
                        {statusLabels[subscription.status] || subscription.status}
                      </span>
                    </td>
                    <td>
                      <div className="cell-stack">
                        <strong>{subscription.billing_interval}</strong>
                        <span className="cell-sub">{subscription.quotation_id ? `Quotation #${subscription.quotation_id}` : 'No quotation linked'}</span>
                      </div>
                    </td>
                    <td>
                      <div className="cell-stack">
                        <strong>{formatDate(subscription.next_billing_date)}</strong>
                        <span className="cell-sub">Last: {formatDate(subscription.last_billing_date)}</span>
                      </div>
                    </td>
                    <td>{renderActions(subscription)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && total > 0 && (
          <div className="table-pagination">
            <span>{total} total subscriptions</span>
            <div>
              <button className="pagination-button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
              <span>Page {page}{pages ? ` of ${pages}` : ''}</span>
              <button className="pagination-button" disabled={page >= pages || pages === 0} onClick={() => setPage((current) => current + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
