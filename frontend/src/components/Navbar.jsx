import { Menu, X } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Logo from './Logo'

const links = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Pricing', href: '#pricing' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  useEffect(() => {
    document.body.classList.toggle('drawer-open', open)
    const handleKeyDown = (event) => { if (event.key === 'Escape') setOpen(false) }
    if (open) document.addEventListener('keydown', handleKeyDown)
    return () => { document.body.classList.remove('drawer-open'); document.removeEventListener('keydown', handleKeyDown) }
  }, [open])

  const go = (href) => {
    setOpen(false)
    if (window.location.pathname !== '/') navigate(`/${href}`)
    else document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' })
  }

  return <>
    <header className="site-navbar">
      <div className="nav-inner">
        <Logo />
        <nav className="desktop-nav" aria-label="Primary navigation">
          {links.map((link) => <a key={link.href} href={link.href}>{link.label}</a>)}
          <Link to="/login">Sign In</Link>
          <Link to="/register" className="button button-dark button-small">Get Started</Link>
        </nav>
        <button className="menu-trigger" onClick={() => setOpen(true)} aria-label="Open menu" aria-expanded={open}><Menu size={18} /> Menu</button>
      </div>
    </header>
    <div className={`mobile-drawer ${open ? 'is-open' : ''}`} aria-hidden={!open}>
      <div className="drawer-header"><Logo /><button className="icon-button" onClick={() => setOpen(false)} aria-label="Close menu"><X /></button></div>
      <nav className="drawer-links" aria-label="Mobile navigation">
        {links.map((link) => <a key={link.href} href={link.href} onClick={(event) => { event.preventDefault(); go(link.href) }}>{link.label}</a>)}
        <Link to="/login" onClick={() => setOpen(false)}>Sign In</Link>
        <Link to="/register" className="button button-dark" onClick={() => setOpen(false)}>Get Started</Link>
      </nav>
      <p className="drawer-footer">© {new Date().getFullYear()} Brightloop. Built for clear operations.</p>
    </div>
  </>
}
