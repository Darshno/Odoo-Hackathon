import { Link } from 'react-router-dom'
import { useState } from 'react'
import AuthShell from '../components/AuthShell'
import { Alert, FormField, PrimaryButton } from '../components/FormControls'
import { forgotPassword } from '../services/auth'
import { errorMessage } from '../utils/validation'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState(''); const [message, setMessage] = useState(''); const [preview, setPreview] = useState(''); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const submit = async (event) => { event.preventDefault(); setLoading(true); setError(''); try { const { data } = await forgotPassword({ email }); setMessage(data.message); setPreview(data.preview_token || '') } catch (err) { setError(errorMessage(err)) } finally { setLoading(false) } }
  return <AuthShell eyebrow="Account recovery" title="Reset your password" footer={<Link to="/login">Back to sign in</Link>}><form onSubmit={submit} className="auth-form"><Alert>{error}</Alert>{message ? <Alert type="success">{message}{preview && <><br /><span className="preview-note">Development preview token: <code>{preview}</code></span></>}</Alert> : null}<FormField label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /><PrimaryButton loading={loading} type="submit">Send reset instructions</PrimaryButton></form></AuthShell>
}
