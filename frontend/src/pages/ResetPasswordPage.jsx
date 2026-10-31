import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import AuthShell from '../components/AuthShell'
import { Alert, FormField, PrimaryButton } from '../components/FormControls'
import { resetPassword } from '../services/auth'
import { errorMessage, validatePassword } from '../utils/validation'

export default function ResetPasswordPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const [form, setForm] = useState({ token: params.get('token') || '', new_password: '', confirm_password: '' }); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const submit = async (event) => { event.preventDefault(); setError(''); const passwordError = validatePassword(form.new_password).join(' · '); if (passwordError) return setError(passwordError); if (form.new_password !== form.confirm_password) return setError('Passwords do not match.'); setLoading(true); try { const { data } = await resetPassword(form); setMessage(data.message); setTimeout(() => navigate('/login'), 1200) } catch (err) { setError(errorMessage(err, 'This reset link is invalid or expired.')) } finally { setLoading(false) } }
  return <AuthShell eyebrow="New credentials" title="Choose a new password" footer={<Link to="/login">Back to sign in</Link>}><form onSubmit={submit} className="auth-form"><Alert>{error}</Alert><Alert type="success">{message}</Alert><FormField label="Reset token" value={form.token} onChange={(e) => setForm({ ...form, token: e.target.value })} required /><FormField label="New password" type="password" autoComplete="new-password" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} required /><FormField label="Confirm new password" type="password" autoComplete="new-password" value={form.confirm_password} onChange={(e) => setForm({ ...form, confirm_password: e.target.value })} required /><PrimaryButton loading={loading} type="submit">Update password</PrimaryButton></form></AuthShell>
}
