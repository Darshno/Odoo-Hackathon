import { ArrowLeft, CheckCircle2, CreditCard, Printer } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Alert, PrimaryButton, SecondaryButton } from '../components/FormControls'
import { useAuth } from '../hooks/AuthContext'
import { activateSubscription, closeSubscription, getSubscription, pauseSubscription, renewSubscription, resumeSubscription } from '../services/subscriptions'
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

const formatDateTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

const formatCurrency = (currency, value) => {
  const code = currency || 'USD'
  const numeric = Number(value ?? 0)
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: code }).format(numeric)
}

export default function SubscriptionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdminStaff = ['ADMIN', 'STAFF'].includes(user?.role)
  const [subscription, setSubscription] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [pendingAction, setPendingAction] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await getSubscription(id)
      setSubscription(data)
    } catch (err) {
      setError(errorMessage(err, 'This subscription could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const canPause = useMemo(() => subscription?.lines?.length > 0 && subscription.lines.every((line) => line.pause_allowed), [subscription])
  const canRenew = useMemo(() => subscription?.lines?.length > 0 && subscription.lines.every((line) => line.renewal_allowed), [subscription])

  const handleLifecycleAction = async (action) => {
    if (!subscription) return
    const shouldConfirm = action === 'close'
    if (shouldConfirm) {
      const confirmed = window.confirm(`Close subscription ${subscription.subscription_number}?`)
      if (!confirmed) return
    }

    setPendingAction(action)
    setError('')
    setNotice('')
    try {
      if (action === 'activate') await activateSubscription(subscription.id)
      if (action === 'pause') await pauseSubscription(subscription.id)
      if (action === 'resume') await resumeSubscription(subscription.id)
      if (action === 'renew') await renewSubscription(subscription.id)
      if (action === 'close') await closeSubscription(subscription.id)
      setNotice(`Subscription ${subscription.subscription_number} was updated.`)
      await load()
    } catch (err) {
      setError(errorMessage(err, `We could not update this subscription.`))
    } finally {
      setPendingAction(null)
    }
  }

  if (loading) return <section className="dashboard-page content-wrap"><div className="table-empty">Loading subscription…</div></section>
  if (error) return <section className="dashboard-page content-wrap"><div className="content-stack"><button className="button button-secondary" onClick={() => navigate('/subscriptions')}><ArrowLeft size={16} /> Back</button><Alert>{error}</Alert></div></section>
  if (!subscription) return null

  const lifecycleButtons = []
  if (isAdminStaff) {
    if (subscription.status === 'ACTIVE') {
      if (canPause) lifecycleButtons.push({ key: 'pause', label: 'Pause' })
      if (canRenew) lifecycleButtons.push({ key: 'renew', label: 'Renew' })
      lifecycleButtons.push({ key: 'close', label: 'Close' })
    }
    if (subscription.status === 'PAUSED') {
      lifecycleButtons.push({ key: 'activate', label: 'Activate' })
      lifecycleButtons.push({ key: 'resume', label: 'Resume' })
      lifecycleButtons.push({ key: 'close', label: 'Close' })
    }
  }

  return (
    <section className="dashboard-page content-wrap">
      <div className="quotation-topbar">
        <button className="button button-secondary" onClick={() => navigate('/subscriptions')}><ArrowLeft size={16} /> Back to subscriptions</button>
        <div className="quotation-topbar-actions">
          <button className="button button-secondary" onClick={() => window.print()}><Printer size={16} /> Print</button>
          {lifecycleButtons.length > 0 && lifecycleButtons.map((button) => (
            <SecondaryButton key={button.key} onClick={() => handleLifecycleAction(button.key)} disabled={pendingAction !== null}>
              {button.label}
            </SecondaryButton>
          ))}
        </div>
      </div>

      {notice && <div className="notice-banner">{notice}</div>}
      <Alert>{error}</Alert>

      <article className="quotation-document subscription-document">
        <header className="quotation-document-header">
          <div>
            <span className="eyebrow">Subscription</span>
            <h1>{subscription.subscription_number}</h1>
          </div>
          <div className="quotation-status-box">
            <span className={`status-pill ${statusClasses[subscription.status] || 'status-draft'}`}>
              {statusLabels[subscription.status] || subscription.status}
            </span>
          </div>
        </header>

        <div className="quotation-meta-grid">
          <div>
            <span className="field-label">Customer</span>
            <strong>{subscription.customer?.full_name}</strong>
            <span className="muted-line">{subscription.customer?.email}</span>
          </div>
          <div>
            <span className="field-label">Quotation</span>
            <strong>#{subscription.quotation_id}</strong>
          </div>
          <div>
            <span className="field-label">Start date</span>
            <strong>{formatDate(subscription.start_date)}</strong>
          </div>
          <div>
            <span className="field-label">Billing interval</span>
            <strong>{subscription.billing_interval}</strong>
          </div>
          <div>
            <span className="field-label">Next billing</span>
            <strong>{formatDate(subscription.next_billing_date)}</strong>
          </div>
          <div>
            <span className="field-label">Last billing</span>
            <strong>{formatDate(subscription.last_billing_date)}</strong>
          </div>
        </div>

        <div className="detail-list subscription-detail-list">
          <div>
            <span>End date</span>
            <strong>{formatDate(subscription.end_date)}</strong>
          </div>
          <div>
            <span>Created at</span>
            <strong>{formatDateTime(subscription.created_at)}</strong>
          </div>
          <div>
            <span>Updated at</span>
            <strong>{formatDateTime(subscription.updated_at)}</strong>
          </div>
        </div>

        <div className="quotation-lines">
          <div className="quotation-lines-header">
            <span>Item</span>
            <span>Qty</span>
            <span>Unit</span>
            <span>Amount</span>
          </div>
          {subscription.lines.map((line) => (
            <div className="quotation-line" key={line.id}>
              <div>
                <strong>{line.product_name}</strong>
                <span>{line.plan_name}{line.variant_name ? ` · ${line.variant_name}` : ''}</span>
              </div>
              <span>{line.quantity}</span>
              <span>{formatCurrency(line.currency, line.unit_price)}</span>
              <span>{formatCurrency(line.currency, line.amount)}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  )
}
