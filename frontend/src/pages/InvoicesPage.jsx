import { Receipt, RefreshCcw, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, PrimaryButton } from '../components/FormControls'
import { PageHeader } from '../components/DashboardPrimitives'
import { useAuth } from '../hooks/AuthContext'
import { listUsers } from '../services/auth'
import { issueInvoice, listInvoices, voidInvoice } from '../services/billing'
import { errorMessage } from '../utils/validation'
import { formatCurrency } from '../utils/currency'

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

export default function InvoicesPage() {
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
    subscription_id: '',
    issue_date_from: '',
    issue_date_to: '',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
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
        subscription_id: filters.subscription_id || undefined,
        issue_date_from: filters.issue_date_from || undefined,
        issue_date_to: filters.issue_date_to || undefined,
      }
      const { data } = await listInvoices(params)
      setItems(data.items || [])
      setPages(data.pages || 0)
      setTotal(data.total || 0)
    } catch (err) {
      setError(errorMessage(err, 'We could not load invoices.'))
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
    }, 250)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    load(page)
  }, [page, filters.search, filters.status, filters.customer_id, filters.subscription_id, filters.issue_date_from, filters.issue_date_to])

  const handleInvoiceAction = async (invoice, action) => {
    const actionLabel = action === 'issue' ? 'issue' : 'void'
    if (action === 'void') {
      const confirmed = window.confirm(`Void invoice ${invoice.invoice_number}?`)
      if (!confirmed) return
    }

    setPendingAction(`${invoice.id}:${action}`)
    setError('')
    setNotice('')
    try {
      if (action === 'issue') await issueInvoice(invoice.id)
      if (action === 'void') await voidInvoice(invoice.id)
      setNotice(`Invoice ${invoice.invoice_number} was ${action === 'issue' ? 'issued' : 'voided'}.`)
      await load(page)
    } catch (err) {
      setError(errorMessage(err, `We could not ${actionLabel} this invoice.`))
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

  return (
    <section className="dashboard-page content-wrap">
      <PageHeader
        eyebrow={isAdminStaff ? 'Billing management' : 'Billing'}
        title="Invoices"
        description={
          isAdminStaff
            ? 'Review issued invoices, track balances, and manage billing workflow.'
            : 'See your invoices, due dates, and payment activity for the current account.'
        }
      />

      <Alert type="success">{notice}</Alert>
      <Alert>{error}</Alert>

      <div className="table-card invoice-table-card">
        <div className="table-toolbar subscription-toolbar">
          <label className="search-box" aria-label="Search invoices">
            <Search size={16} />
            <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search by invoice number, customer, or email" />
          </label>

          <label className="subscription-filter-item">
            <span>Status</span>
            <select value={filters.status} onChange={(event) => {
              setFilters((current) => ({ ...current, status: event.target.value }))
              setPage(1)
            }}>
              <option value="">All statuses</option>
              {Object.entries(statusLabels).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </label>

          {customerFilter}

          <label className="subscription-filter-item">
            <span>Subscription</span>
            <input
              type="number"
              min="1"
              value={filters.subscription_id}
              onChange={(event) => {
                setFilters((current) => ({ ...current, subscription_id: event.target.value }))
                setPage(1)
              }}
              placeholder="ID"
            />
          </label>

          <label className="subscription-filter-item">
            <span>From</span>
            <input type="date" value={filters.issue_date_from} onChange={(event) => {
              setFilters((current) => ({ ...current, issue_date_from: event.target.value }))
              setPage(1)
            }} />
          </label>

          <label className="subscription-filter-item">
            <span>To</span>
            <input type="date" value={filters.issue_date_to} onChange={(event) => {
              setFilters((current) => ({ ...current, issue_date_to: event.target.value }))
              setPage(1)
            }} />
          </label>

          <button className="button button-secondary refresh-button" type="button" onClick={() => load(page)}>
            <RefreshCcw size={15} /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="table-empty">Loading invoices…</div>
        ) : items.length === 0 ? (
          <div className="table-empty">No invoices match the current filters.</div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Issued</th>
                  <th>Due</th>
                  <th>Total</th>
                  <th>Due now</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>
                      <Link to={`/invoices/${invoice.id}`} className="table-name-button">
                        <strong>{invoice.invoice_number}</strong>
                        <span className="cell-sub">Sub #{invoice.subscription_id}</span>
                      </Link>
                    </td>
                    <td>
                      <div className="cell-stack">
                        <strong>{invoice.customer?.full_name || '—'}</strong>
                        <span className="cell-sub">{invoice.customer?.email || '—'}</span>
                      </div>
                    </td>
                    <td><span className={`status-pill ${statusClasses[invoice.status] || 'status-draft'}`}>{statusLabels[invoice.status] || invoice.status}</span></td>
                    <td>{formatDate(invoice.issue_date)}</td>
                    <td>{formatDate(invoice.due_date)}</td>
                    <td>{formatCurrency(invoice.currency, invoice.total)}</td>
                    <td>{formatCurrency(invoice.currency, invoice.amount_due)}</td>
                    <td>
                      <div className="table-actions-row">
                        <Link to={`/invoices/${invoice.id}`} className="table-text-link">View</Link>
                        {isAdminStaff && invoice.status === 'DRAFT' && (
                          <button className="mini-button subtle" disabled={pendingAction === `${invoice.id}:issue`} onClick={() => handleInvoiceAction(invoice, 'issue')}>
                            Issue
                          </button>
                        )}
                        {isAdminStaff && invoice.status !== 'PAID' && invoice.status !== 'VOID' && (
                          <button className="mini-button reject" disabled={pendingAction === `${invoice.id}:void`} onClick={() => handleInvoiceAction(invoice, 'void')}>
                            Void
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && total > 0 && (
          <div className="table-pagination">
            <span>{total} total invoices</span>
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
