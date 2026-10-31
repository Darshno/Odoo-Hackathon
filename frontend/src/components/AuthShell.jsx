import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function AuthShell({ eyebrow, title, children, footer }) {
  return <main className="auth-page"><div className="auth-top"><Logo /><Link to="/" className="back-link">Back to home</Link></div><div className="auth-card"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{children}</div>{footer && <p className="auth-footer">{footer}</p>}</main>
}
