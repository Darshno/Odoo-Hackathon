import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import AuthShell from '../components/AuthShell'
import { Alert, FormField, PrimaryButton } from '../components/FormControls'
import { errorMessage, validatePassword } from '../utils/validation'
import { useAuth } from '../hooks/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth(); const navigate = useNavigate(); const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm_password: '' }); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const passwordError = form.password ? validatePassword(form.password).join(' · ') : ''
  const submit = async (event) => { event.preventDefault(); setError(''); if (form.password !== form.confirm_password) return setError('Passwords do not match.'); if (passwordError) return setError(passwordError); setLoading(true); try { const user = await register(form); navigate(user?.role === 'CUSTOMER' ? '/my-quotations' : '/dashboard', { replace: true }) } catch (err) { setError(errorMessage(err, 'We could not create your account.')) } finally { setLoading(false) } }
  return <AuthShell eyebrow="Create your workspace" title="Start with Brightloop" footer={<>Already have an account? <Link to="/login">Sign in</Link></>}><form onSubmit={submit} className="auth-form"><Alert>{error}</Alert><FormField label="Full name" autoComplete="name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required /><FormField label="Email" type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /><FormField label="Password" type="password" autoComplete="new-password" hint="9+ characters with uppercase, lowercase, and a special character." error={passwordError} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /><FormField label="Confirm password" type="password" autoComplete="new-password" value={form.confirm_password} onChange={(e) => setForm({ ...form, confirm_password: e.target.value })} required /><PrimaryButton loading={loading} type="submit">Create account</PrimaryButton></form></AuthShell>
}
