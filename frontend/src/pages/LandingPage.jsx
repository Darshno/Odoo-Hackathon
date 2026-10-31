import { ArrowRight, BarChart3, Check, CreditCard, FileText, Package, Repeat2, ShieldCheck, Sparkles, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'

const features = [
  ['Product Management', 'Organize products, pricing, and product variants.', Package],
  ['Subscription Plans', 'Configure billing cycles, availability, and plan settings.', Repeat2],
  ['Subscription Lifecycle', 'Manage subscriptions from quotation to activation and closure.', Sparkles],
  ['Automated Invoicing', 'Generate invoices for subscriptions when billing is due.', FileText],
  ['Payment Tracking', 'Record payments and track invoice status.', CreditCard],
  ['Revenue Analytics', 'Understand subscription activity and revenue.', BarChart3],
]
const ticker = ['Subscription Management', 'Recurring Billing', 'Invoice Tracking', 'Payment Management', 'Customer Management']

export default function LandingPage() {
  return <>
    <section className="hero-section"><div className="hero-lines" aria-hidden="true"><span /><span /><span /></div><div className="hero-content"><span className="eyebrow hero-eyebrow">The calm center of recurring revenue</span><h1>Subscriptions,<br /><em>managed smarter.</em></h1><p>Manage products, subscription plans, recurring invoices, and payments in one place.</p><div className="hero-actions"><Link to="/register" className="button button-dark">Get Started <ArrowRight size={17} /></Link><a href="#features" className="button button-secondary">Explore Features</a></div><div className="hero-note"><Check size={15} /> Phase 1 foundation, designed for what comes next.</div></div></section>
    <div className="ticker-wrap" aria-label="Planned capabilities"><div className="ticker-track">{[...ticker, ...ticker].map((item, index) => <span className="ticker-pill" key={`${item}-${index}`}>{item}</span>)}</div></div>
    <section id="features" className="section section-features"><div className="section-intro"><span className="eyebrow">Planned capabilities</span><h2>Everything you need to manage <em>subscriptions.</em></h2><p>Keep products, plans, customers, and billing workflows organized in one place. These are planned product capabilities for future phases.</p></div><div className="feature-grid">{features.map(([title, copy, Icon]) => <article className="feature-card" key={title}><div className="feature-icon"><Icon size={20} /></div><h3>{title}</h3><p>{copy}</p><span className="feature-status">Planned for a later phase</span></article>)}</div></section>
    <section id="how-it-works" className="section process-section"><div className="section-intro"><span className="eyebrow">How it works</span><h2>A clearer path from offer to <em>outcome.</em></h2></div><div className="process-list">{[['01', 'Add Products', 'Organize the products you offer.'], ['02', 'Configure Plans', 'Set billing cycles and plan rules.'], ['03', 'Manage Subscriptions', 'Organize customer subscriptions and their lifecycle.'], ['04', 'Track Billing', 'Generate invoices and record payments.']].map(([number, title, copy]) => <div className="process-row" key={number}><span className="process-number">{number}</span><h3>{title}</h3><p>{copy}</p></div>)}</div></section>
    <section id="pricing" className="section cta-section"><div className="cta-panel"><div className="cta-orbit" aria-hidden="true" /><span className="eyebrow">Start with the foundation</span><h2>Your subscriptions.<br /><em>Under control.</em></h2><p>Bring your subscription workflow into one organized workspace.</p><Link to="/register" className="button button-dark">Get Started <ArrowRight size={17} /></Link></div></section>
  </>
}
