import { CheckCircle2, RefreshCcw, Search, XCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, PrimaryButton } from '../components/FormControls'
import { PageHeader } from '../components/DashboardPrimitives'
import { acceptQuotation, listQuotations, rejectQuotation } from '../services/auth'
import { errorMessage } from '../utils/validation'
import { formatCurrency } from '../utils/currency'

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

export default function MyQuotationsPage() {
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [pages, setPages] = useState(0)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [pendingAction, setPendingAction] = useState(null)
  const [notice, setNotice] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await listQuotations({ page, page_size: pageSize, status: status || undefined })
      setItems(data.items || [])
      setPages(data.pages || 0)
      setTotal(data.total || 0)
    } catch (err) {
      setError(errorMessage(err, 'We could not load your quotations.'))
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, status])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return items
    return items.filter((item) => item.quotation_number.toLowerCase().includes(query))
  }, [items, search])

  const handleAction = async (quotation, action) => {
    const actionLabel = action === 'accept' ? 'accept' : 'reject'
    const confirmed = window.confirm(`Are you sure you want to ${actionLabel} quotation ${quotation.quotation_number}?`)
    if (!confirmed) return

    setPendingAction(quotation.id)
    setNotice('')
    try {
      if (action === 'accept') await acceptQuotation(quotation.id)
      else await rejectQuotation(quotation.id)
      setNotice(`Quotation ${quotation.quotation_number} has been ${action === 'accept' ? 'accepted' : 'rejected'}.`)
      await load()
    } catch (err) {
      setError(errorMessage(err, `We could not ${actionLabel} this quotation.`))
    } finally {
      setPendingAction(null)
    }
  }

  return <section className="dashboard-page content-wrap">
    <PageHeader
      eyebrow="Customer workspace"
      title="My Quotations"
      description="Review the quotations sent to your account and respond when action is available."
    />
    <div className="quotation-shell">
      <div className="table-card quotation-card-table">
        <div className="table-toolbar">
          <label className="search-box" aria-label="Search quotations">
            <Search size={16} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by quotation number" />
          </label>
          <select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter quotations by status">
            <option value="">All statuses</option>
            {Object.keys(statusLabels).map((key) => <option key={key} value={key}>{statusLabels[key]}</option>)}
          </select>
          <PrimaryButton onClick={() => { setPage(1); load() }} type="button" className="refresh-button"><RefreshCcw size={15} /> Refresh</PrimaryButton>
        </div>

        {notice && <div className="notice-banner">{notice}</div>}
        {error && <Alert>{error}</Alert>}

        {loading ? <div className="table-empty">Loading quotations…</div> : filtered.length === 0 ? <div className="table-empty">No quotations match your current filters.</div> : <div className="table-scroll"><table>
          <thead>
            <tr>
              <th>Quotation</th>
              <th>Status</th>
              <th>Created</th>
              <th>Valid until</th>
              <th>Total</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((quotation) => {
              const canAct = quotation.status === 'SENT'
              return <tr key={quotation.id}>
                <td>
                  <Link to={`/quotations/${quotation.id}`} className="table-name-button">
                    <strong>{quotation.quotation_number}</strong>
                    <span className="cell-sub">{quotation.customer?.full_name || 'Customer'}</span>
                  </Link>
                </td>
                <td><span className={`status-pill ${statusClasses[quotation.status] || 'status-draft'}`}>{statusLabels[quotation.status] || quotation.status}</span></td>
                <td>{formatDate(quotation.created_at?.slice(0, 10))}</td>
                <td>{formatDate(quotation.valid_until)}</td>
                <td>{formatCurrency(quotation.currency, quotation.total)}</td>
                <td>
                  <div className="table-actions-row">
                    <Link to={`/quotations/${quotation.id}`} className="table-text-link">View</Link>
                    {canAct && <>
                      <button className="mini-button accept" disabled={pendingAction === quotation.id} onClick={() => handleAction(quotation, 'accept')}><CheckCircle2 size={14} /> Accept</button>
                      <button className="mini-button reject" disabled={pendingAction === quotation.id} onClick={() => handleAction(quotation, 'reject')}><XCircle size={14} /> Reject</button>
                    </>}
                  </div>
                </td>
              </tr>
            })}
          </tbody>
        </table></div>}

        {!loading && total > 0 && <div className="table-pagination"><span>{total} quotation{total === 1 ? '' : 's'}</span><div>
          <button className="pagination-button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
          <span>Page {page}{pages ? ` of ${pages}` : ''}</span>
          <button className="pagination-button" disabled={page >= pages || pages === 0} onClick={() => setPage((current) => current + 1)}>Next</button>
        </div></div>}
      </div>
    </div>
  </section>
}
