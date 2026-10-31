import { ArrowLeft, CheckCircle2, Printer, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Alert, PrimaryButton, SecondaryButton } from '../components/FormControls'
import { acceptQuotation, getQuotation, rejectQuotation } from '../services/auth'
import { errorMessage } from '../utils/validation'

const statusLabels = {
  DRAFT: 'Draft',
  SENT: 'Awaiting your response',
  ACCEPTED: 'Accepted',
  REJECTED: 'Rejected',
  CANCELLED: 'Cancelled',
  EXPIRED: 'Expired',
}

const statusClasses = {
  DRAFT: 'status-draft',
  SENT: 'status-sent',
  ACCEPTED: 'status-accepted',
  REJECTED: 'status-rejected',
  CANCELLED: 'status-cancelled',
  EXPIRED: 'status-expired',
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

export default function QuotationDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [quotation, setQuotation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [pendingAction, setPendingAction] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await getQuotation(id)
      setQuotation(data)
    } catch (err) {
      setError(errorMessage(err, 'This quotation could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const canAct = quotation?.status === 'SENT'

  const handleAction = async (action) => {
    if (!quotation) return
    const actionLabel = action === 'accept' ? 'accept' : 'reject'
    const confirmText = action === 'accept'
      ? `Accept quotation ${quotation.quotation_number}?`
      : `Reject quotation ${quotation.quotation_number}?`

    const confirmed = window.confirm(confirmText)
    if (!confirmed) return

    setPendingAction(action)
    try {
      if (action === 'accept') await acceptQuotation(quotation.id)
      else await rejectQuotation(quotation.id)
      await load()
    } catch (err) {
      setError(errorMessage(err, `We could not ${actionLabel} this quotation.`))
    } finally {
      setPendingAction(null)
    }
  }

  if (loading) return <section className="dashboard-page content-wrap"><div className="table-empty">Loading quotation…</div></section>
  if (error) return <section className="dashboard-page content-wrap"><div className="content-stack"><button className="button button-secondary" onClick={() => navigate('/my-quotations')}><ArrowLeft size={16} /> Back</button><Alert>{error}</Alert></div></section>
  if (!quotation) return null

  return <section className="dashboard-page content-wrap">
    <div className="quotation-topbar">
      <button className="button button-secondary" onClick={() => navigate('/my-quotations')}><ArrowLeft size={16} /> Back to quotations</button>
      <div className="quotation-topbar-actions">
        <button className="button button-secondary" onClick={() => window.print()}><Printer size={16} /> Print</button>
        {canAct && <>
          <PrimaryButton onClick={() => handleAction('accept')} disabled={pendingAction !== null} loading={pendingAction === 'accept'}><CheckCircle2 size={15} /> Accept</PrimaryButton>
          <SecondaryButton onClick={() => handleAction('reject')} disabled={pendingAction !== null}><XCircle size={15} /> Reject</SecondaryButton>
        </>}
      </div>
    </div>

    <article className="quotation-document">
      <header className="quotation-document-header">
        <div>
          <span className="eyebrow">Quotation</span>
          <h1>{quotation.quotation_number}</h1>
        </div>
        <div className="quotation-status-box">
          <span className={`status-pill ${statusClasses[quotation.status] || 'status-draft'}`}>{statusLabels[quotation.status] || quotation.status}</span>
        </div>
      </header>

      <div className="quotation-meta-grid">
        <div>
          <span className="field-label">Customer</span>
          <strong>{quotation.customer?.full_name}</strong>
          <span className="muted-line">{quotation.customer?.email}</span>
        </div>
        <div>
          <span className="field-label">Created</span>
          <strong>{formatDate(quotation.created_at?.slice(0, 10))}</strong>
        </div>
        <div>
          <span className="field-label">Valid until</span>
          <strong>{formatDate(quotation.valid_until)}</strong>
        </div>
        <div>
          <span className="field-label">Total</span>
          <strong>{formatCurrency(quotation.currency, quotation.total)}</strong>
        </div>
      </div>

      {quotation.notes && <div className="quotation-notes"><strong>Notes</strong><p>{quotation.notes}</p></div>}

      <div className="quotation-lines">
        <div className="quotation-lines-header">
          <span>Item</span>
          <span>Qty</span>
          <span>Unit</span>
          <span>Total</span>
        </div>
        {quotation.lines.map((line) => <div className="quotation-line" key={line.id}>
          <div>
            <strong>{line.product_name}</strong>
            <span>{line.plan_name}{line.variant_name ? ` · ${line.variant_name}` : ''}</span>
          </div>
          <span>{line.quantity}</span>
          <span>{formatCurrency(quotation.currency, line.unit_price)}</span>
          <span>{formatCurrency(quotation.currency, line.line_total)}</span>
        </div>)}
      </div>

      <div className="quotation-totals">
        <div>
          <span>Subtotal</span>
          <strong>{formatCurrency(quotation.currency, quotation.subtotal)}</strong>
        </div>
        <div>
          <span>Final total</span>
          <strong>{formatCurrency(quotation.currency, quotation.total)}</strong>
        </div>
      </div>

      {quotation.status === 'ACCEPTED' && <div className="accepted-banner"><CheckCircle2 size={18} /> Your quotation has been accepted. Subscription activation and billing will be available through the upcoming subscription workflow.</div>}
      {quotation.status === 'REJECTED' && <div className="rejected-banner"><XCircle size={18} /> This quotation has been rejected.</div>}

      <div className="document-footer-note">
        <Link to="/plans" className="inline-link">Browse plans</Link>
      </div>
    </article>
  </section>
}
