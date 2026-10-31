import { Link } from 'react-router-dom'

export default function Logo({ dark = false }) {
  return (
    <Link className={`logo ${dark ? 'logo-dark' : ''}`} to="/" aria-label="Brightloop home">
      <span className="logo-mark" aria-hidden="true" />
      <span>Brightloop</span>
    </Link>
  )
}
