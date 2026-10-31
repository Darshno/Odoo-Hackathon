import { Eye, Plus, Search, UserCheck, UserX, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createStaff, getUser, listUsers, updateUserStatus } from '../services/auth'
import { Alert, FormField, PrimaryButton, SecondaryButton, StatusBadge } from '../components/FormControls'
import { PageHeader } from '../components/DashboardPrimitives'
import { errorMessage } from '../utils/validation'

const emptyStaff = { full_name: '', email: '', password: '', confirm_password: '' }

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [meta, setMeta] = useState({ page: 1, pages: 0, total: 0 })
  const [filters, setFilters] = useState({ search: '', role: '', is_active: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showStaff, setShowStaff] = useState(false)
  const [staff, setStaff] = useState(emptyStaff)
  const [saving, setSaving] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)

  const load = async (page = 1) => {
    setLoading(true)
    try {
      const params = {
        page,
        page_size: 8,
        search: filters.search || undefined,
        role: filters.role || undefined,
        is_active: filters.is_active === '' ? undefined : filters.is_active === 'true',
      }
      const { data } = await listUsers(params)
      setUsers(data.items)
      setMeta(data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(1) }, [filters.search, filters.role, filters.is_active])

  const toggle = async (user) => {
    if (!window.confirm(`${user.is_active ? 'Deactivate' : 'Activate'} ${user.full_name}?`)) return
    try {
      await updateUserStatus(user.id, !user.is_active)
      setNotice('Account status updated.')
      load(meta.page)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const viewDetails = async (id) => {
    try {
      const { data } = await getUser(id)
      setSelectedUser(data)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const submitStaff = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await createStaff(staff)
      setNotice('Staff account created.')
      setStaff(emptyStaff)
      setShowStaff(false)
      load(1)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return <section className="dashboard-page content-wrap">
    <PageHeader eyebrow="Admin workspace" title="User management" description="Keep access clear for every Brightloop workspace member." actions={<PrimaryButton onClick={() => setShowStaff(true)}><Plus size={16} /> Create staff</PrimaryButton>} />
    <Alert type="success">{notice}</Alert>
    <Alert>{error}</Alert>
    <div className="table-card">
      <div className="table-toolbar">
        <label className="search-box"><Search size={17} /><input placeholder="Search by name or email" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} /></label>
        <select value={filters.role} onChange={(e) => setFilters({ ...filters, role: e.target.value })}><option value="">All roles</option><option value="ADMIN">Admin</option><option value="STAFF">Staff</option><option value="CUSTOMER">Customer</option></select>
        <select value={filters.is_active} onChange={(e) => setFilters({ ...filters, is_active: e.target.value })}><option value="">All statuses</option><option value="true">Active</option><option value="false">Inactive</option></select>
      </div>
      {loading ? <div className="table-empty">Loading users…</div> : users.length === 0 ? <div className="table-empty">No users match these filters.</div> : <div className="table-scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td><button className="table-name-button" onClick={() => viewDetails(user.id)}><strong>{user.full_name}</strong><span className="cell-sub">Joined {new Date(user.created_at).toLocaleDateString()}</span></button></td><td>{user.email}</td><td><span className="role-pill">{user.role}</span></td><td><StatusBadge active={user.is_active} /></td><td><div className="table-actions"><button className="table-action" onClick={() => viewDetails(user.id)} title="View details" aria-label={`View details for ${user.full_name}`}><Eye size={16} /></button><button className="table-action" onClick={() => toggle(user)} title={user.is_active ? 'Deactivate' : 'Activate'} aria-label={`${user.is_active ? 'Deactivate' : 'Activate'} ${user.full_name}`}>{user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}</button></div></td></tr>)}</tbody></table></div>}
      <div className="table-pagination"><span>{meta.total} total users</span><div><button className="pagination-button" disabled={meta.page <= 1} onClick={() => load(meta.page - 1)}>Previous</button><span>Page {meta.page} of {Math.max(meta.pages, 1)}</span><button className="pagination-button" disabled={!meta.pages || meta.page >= meta.pages} onClick={() => load(meta.page + 1)}>Next</button></div></div>
    </div>
    {showStaff && <div className="modal-backdrop"><div className="modal-card"><div className="modal-header"><div><span className="eyebrow">Admin action</span><h2>Create staff account</h2></div><button className="icon-button" onClick={() => setShowStaff(false)} aria-label="Close"><X /></button></div><form onSubmit={submitStaff} className="auth-form"><FormField label="Full name" value={staff.full_name} onChange={(e) => setStaff({ ...staff, full_name: e.target.value })} required /><FormField label="Email" type="email" value={staff.email} onChange={(e) => setStaff({ ...staff, email: e.target.value })} required /><FormField label="Temporary password" type="password" hint="9+ characters with uppercase, lowercase, and a special character." value={staff.password} onChange={(e) => setStaff({ ...staff, password: e.target.value })} required /><FormField label="Confirm password" type="password" value={staff.confirm_password} onChange={(e) => setStaff({ ...staff, confirm_password: e.target.value })} required /><div className="modal-actions"><SecondaryButton type="button" onClick={() => setShowStaff(false)}>Cancel</SecondaryButton><PrimaryButton loading={saving} type="submit">Create account</PrimaryButton></div></form></div></div>}
    {selectedUser && <div className="modal-backdrop"><div className="modal-card detail-modal"><div className="modal-header"><div><span className="eyebrow">Account detail</span><h2>{selectedUser.full_name}</h2></div><button className="icon-button" onClick={() => setSelectedUser(null)} aria-label="Close"><X /></button></div><div className="detail-list"><div><span>Email</span><strong>{selectedUser.email}</strong></div><div><span>Role</span><strong>{selectedUser.role}</strong></div><div><span>Status</span><StatusBadge active={selectedUser.is_active} /></div><div><span>Created</span><strong>{new Date(selectedUser.created_at).toLocaleString()}</strong></div><div><span>Last updated</span><strong>{new Date(selectedUser.updated_at).toLocaleString()}</strong></div></div></div></div>}
  </section>
}
