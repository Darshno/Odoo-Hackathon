import { useState } from 'react'
import { useAuth } from '../hooks/AuthContext'
import { updateProfile } from '../services/auth'
import { Alert, FormField, PrimaryButton, StatusBadge } from '../components/FormControls'
import { PageHeader } from '../components/DashboardPrimitives'
import { errorMessage } from '../utils/validation'

export default function ProfilePage() {
  const { user, setUser } = useAuth(); const [name, setName] = useState(user.full_name); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const submit = async (event) => { event.preventDefault(); setLoading(true); setMessage(''); setError(''); try { const { data } = await updateProfile({ full_name: name }); setUser(data); setMessage('Profile updated.') } catch (err) { setError(errorMessage(err)) } finally { setLoading(false) } }
  return <section className="dashboard-page content-wrap"><PageHeader eyebrow="Your profile" title="Keep your details current." description="Only your permitted profile fields can be changed here." /><div className="profile-layout"><div className="settings-card"><Alert type="success">{message}</Alert><Alert>{error}</Alert><form onSubmit={submit} className="auth-form"><FormField label="Full name" value={name} onChange={(e) => setName(e.target.value)} required /><div className="readonly-field"><span className="field-label">Email</span><strong>{user.email}</strong><span className="field-hint">Email changes are managed by an administrator.</span></div><PrimaryButton loading={loading} type="submit">Save changes</PrimaryButton></form></div><aside className="profile-aside"><span className="eyebrow">Account status</span><StatusBadge active={user.is_active}>{user.is_active ? 'Active account' : 'Inactive account'}</StatusBadge><span className="profile-role">{user.role} access</span></aside></div></section>
}
