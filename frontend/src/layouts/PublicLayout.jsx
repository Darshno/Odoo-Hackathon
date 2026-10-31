import { Outlet } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Logo from '../components/Logo'

export default function PublicLayout() {
  return <div className="public-shell"><Navbar /><main><Outlet /></main><footer className="site-footer"><div className="footer-inner"><div><Logo /><p className="footer-copy">A calmer foundation for recurring revenue operations.</p></div><div className="footer-links"><a href="/#features">Features</a><a href="/#how-it-works">How It Works</a><a href="/login">Sign In</a><a href="/register">Get Started</a></div><span className="footer-meta">© {new Date().getFullYear()} Brightloop</span></div></footer></div>
}
