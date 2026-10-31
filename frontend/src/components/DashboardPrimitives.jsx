export function PageHeader({ eyebrow, title, description, actions }) {
  return <div className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="header-actions">{actions}</div>}</div>
}

export function DashboardCard({ label, value, detail, icon: Icon }) {
  return <div className="dashboard-card"><div className="card-icon">{Icon && <Icon size={18} />}</div><span className="card-label">{label}</span><strong className="card-value">{value}</strong>{detail && <span className="card-detail">{detail}</span>}</div>
}

export function EmptyState({ title, description }) { return <div className="empty-state"><span className="empty-orb" /><h3>{title}</h3><p>{description}</p></div> }
