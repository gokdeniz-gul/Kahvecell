import { Coffee } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Logo({ to = '/' }) {
  return (
    <Link to={to} className="logo" aria-label="KahveCell ana sayfa">
      <span className="logo__mark">
        <Coffee size={20} strokeWidth={2.5} />
      </span>
      <span className="logo__text">
        Kahve<span>Cell</span>
      </span>
    </Link>
  )
}
