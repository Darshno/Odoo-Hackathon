import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import AuthShell from '../components/AuthShell'
import { Alert, FormField, PrimaryButton } from '../components/FormControls'
import { errorMessage } from '../utils/validation'
import { useAuth } from '../hooks/AuthContext'

export default function LoginPage() {
  const { login } = useAuth(); const navigate = useNavigate(); const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' }); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const submit = async (event) => { event.preventDefault(); setError(''); setLoading(true); try { const user = await login(form); const destination = location.state?.from || (user?.role === 'CUSTOMER' ? '/my-quotations' : '/dashboard'); navigate(destination, { replace: true }) } catch (err) { setError(errorMessage(err, 'We could not sign you in.')) } finally { setLoading(false) } }
  return <AuthShell eyebrow="Welcome back" title="Sign in to Brightloop" footer={<>New to Brightloop? <Link to="/register">Create an account</Link></>}><form onSubmit={submit} className="auth-form"><Alert>{error}</Alert><FormField label="Email" type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /><FormField label="Password" type="password" autoComplete="current-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /><div className="form-row-end"><Link to="/forgot-password" className="text-link">Forgot password?</Link></div><PrimaryButton loading={loading} type="submit">Sign In</PrimaryButton></form></AuthShell>
}
