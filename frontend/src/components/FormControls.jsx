import { LoaderCircle } from 'lucide-react'

export function PrimaryButton({ children, loading = false, className = '', ...props }) {
  return <button className={`button button-primary ${className}`} disabled={loading || props.disabled} {...props}>{loading ? <><LoaderCircle className="spin" size={17} /> Working…</> : children}</button>
}

export function SecondaryButton({ children, className = '', ...props }) {
  return <button className={`button button-secondary ${className}`} {...props}>{children}</button>
}

export function FormField({ label, error, hint, ...props }) {
  return <label className="form-field">
    <span className="field-label">{label}</span>
    <input className={`text-input ${error ? 'has-error' : ''}`} {...props} />
    {hint && !error ? <span className="field-hint">{hint}</span> : null}
    {error ? <span className="field-error">{error}</span> : null}
  </label>
}

export function Alert({ type = 'error', children }) {
  if (!children) return null
  return <div className={`alert alert-${type}`} role={type === 'error' ? 'alert' : 'status'}>{children}</div>
}

export function StatusBadge({ active, children }) {
  return <span className={`status-badge ${active ? 'status-active' : 'status-inactive'}`}><span className="status-dot" />{children || (active ? 'Active' : 'Inactive')}</span>
}
