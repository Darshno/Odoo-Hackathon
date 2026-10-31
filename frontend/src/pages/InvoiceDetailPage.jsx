import { ArrowLeft, Receipt } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, PrimaryButton, SecondaryButton } from '../components/FormControls'
import { useAuth } from '../hooks/AuthContext'
import { getInvoice, issueInvoice, voidInvoice } from '../services/billing'
import { errorMessage } from '../utils/validation'

const statusLabels = {
  DRAFT: 'Draft',
  ISSUED: 'Issued',
  PARTIALLY_PAID: 'Partially paid',
  PAID: 'Paid',
  OVERDUE: 'Overdue',
  VOID: 'Voided',
}

const statusClasses = {
  DRAFT: 'status-draft',
  ISSUED: 'status-sent',
  PARTIALLY_PAID: 'status-sent',
  PAID: 'status-accepted',
  OVERDUE: 'status-rejected',
  VOID: 'status-cancelled',
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
  if (Number.isNaN(date.getTime())) return date.toISOString()
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

const formatCurrency = (currency, value) => {
  const code = currency || 'USD'
  const numeric = Number(value ?? 0)
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: code }).format(numeric)
}

export default function InvoiceDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdminStaff = ['ADMIN', 'STAFF'].includes(user?.role)
  const [invoice, setInvoice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [pendingAction, setPendingAction] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await getInvoice(id)
      setInvoice(data)
    } catch (err) {
      setError(errorMessage(err, 'This invoice could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const handleAction = async (action) => {
    if (!invoice) return
    if (action === 'void') {
      const confirmed = window.confirm(`Void invoice ${invoice.invoice_number}?`)
      if (!confirmed) return
    }

    setPendingAction(action)
    setError('')
    setNotice('')
    try {
      if (action === 'issue') await issueInvoice(invoice.id)
      if (action === 'void') await voidInvoice(invoice.id)
      setNotice(`Invoice ${invoice.invoice_number} was ${action === 'issue' ? 'issued' : 'voided'}.`)
      await load()
    } catch (err) {
      setError(errorMessage(err, `We could not ${action === 'issue' ? 'issue' : 'void'} this invoice.`))
    } finally {
      setPendingAction(null)
    }
  }

  if (loading) return <section className="dashboard-page content-wrap"><div className="table-empty">Loading invoice…</div></section>
  if (error) return <section className="dashboard-page content-wrap"><div className="content-stack"><button className="button button-secondary" onClick={() => navigate('/invoices')}><ArrowLeft size={16} /> Back</button><Alert>{error}</Alert></div></section>
  if (!invoice) return null

  return (
    <section className="dashboard-page content-wrap">
      <div className="quotation-topbar">
        <button className="button button-secondary" onClick={() => navigate('/invoices')}><ArrowLeft size={16} /> Back to invoices</button>
        <div className="quotation-topbar-actions">
          {isAdminStaff && invoice.status === 'DRAFT' && (
            <PrimaryButton onClick={() => handleAction('issue')} loading={pendingAction === 'issue'}>
              Issue invoice
            </PrimaryButton>
          )}
          {isAdminStaff && invoice.status !== 'PAID' && invoice.status !== 'VOID' && (
            <SecondaryButton onClick={() => handleAction('void')} disabled={pendingAction !== null}>
              Void invoice
            </SecondaryButton>
          )}
        </div>
      </div>

      {notice && <div className="notice-banner">{notice}</div>}
      <Alert>{error}</Alert>

      <article className="quotation-document invoice-document">
        <header className="quotation-document-header">
          <div>
            <span className="eyebrow">Invoice</span>
            <h1>{invoice.invoice_number}</h1>
          </div>
          <div className="quotation-status-box">
            <span className={`status-pill ${statusClasses[invoice.status] || 'status-draft'}`}>{statusLabels[invoice.status] || invoice.status}</span>
          </div>
        </header>

        <div className="quotation-meta-grid">
          <div>
            <span className="field-label">Customer</span>
            <strong>{invoice.customer?.full_name}</strong>
            <span className="muted-line">{invoice.customer?.email}</span>
          </div>
          <div>
            <span className="field-label">Subscription</span>
            <strong>#{invoice.subscription_id}</strong>
          </div>
          <div>
            <span className="field-label">Issue date</span>
            <strong>{formatDate(invoice.issue_date)}</strong>
          </div>
          <div>
            <span className="field-label">Due date</span>
            <strong>{formatDate(invoice.due_date)}</strong>
          </div>
          <div>
            <span className="field-label">Billing period</span>
            <strong>{formatDate(invoice.billing_period_start)} – {formatDate(invoice.billing_period_end)}</strong>
          </div>
          <div>
            <span className="field-label">Current balance</span>
            <strong>{formatCurrency(invoice.currency, invoice.amount_due)}</strong>
          </div>
        </div>

        {invoice.notes && <div className="quotation-notes"><strong>Notes</strong><p>{invoice.notes}</p></div>}

        <div className="quotation-lines">
          <div className="quotation-lines-header">
            <span>Item</span>
            <span>Qty</span>
            <span>Unit</span>
            <span>Line total</span>
          </div>
          {invoice.lines.map((line) => (
            <div className="quotation-line" key={line.id}>
              <div>
                <strong>{line.product_name}</strong>
                <span>{line.plan_name}{line.variant_name ? ` · ${line.variant_name}` : ''}</span>
              </div>
              <span>{line.quantity}</span>
              <span>{formatCurrency(line.currency, line.unit_price)}</span>
              <span>{formatCurrency(line.currency, line.line_total)}</span>
            </div>
          ))}
        </div>

        <div className="quotation-totals">
          <div><span>Subtotal</span><strong>{formatCurrency(invoice.currency, invoice.subtotal)}</strong></div>
          <div><span>Discount</span><strong>{formatCurrency(invoice.currency, invoice.discount_total)}</strong></div>
          <div><span>Tax</span><strong>{formatCurrency(invoice.currency, invoice.tax_total)}</strong></div>
          <div><span>Total</span><strong>{formatCurrency(invoice.currency, invoice.total)}</strong></div>
          <div><span>Paid</span><strong>{formatCurrency(invoice.currency, invoice.amount_paid)}</strong></div>
          <div><span>Outstanding</span><strong>{formatCurrency(invoice.currency, invoice.amount_due)}</strong></div>
        </div>

        {invoice.payments?.length > 0 && (
          <div className="invoice-payment-history">
            <h3>Payment history</h3>
            <div className="invoice-payment-row">
              <span>Allocation</span>
              <span>Amount</span>
            </div>
            {invoice.payments.map((payment, index) => (
              <div key={`${payment.invoice_id}-${index}`} className="invoice-payment-row">
                <span>Payment {index + 1}</span>
                <strong>{formatCurrency(invoice.currency, payment.amount)}</strong>
              </div>
            ))}
          </div>
        )}
      </article>
    </section>
  )
}
