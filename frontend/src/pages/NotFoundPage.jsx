import { Compass } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/StateViews'

export default function NotFoundPage() {
  return (
    <div className="page">
      <EmptyState icon={Compass} title="Sayfa bulunamadı"
        action={<Link to="/" className="btn btn--primary btn--sm">Ana sayfaya dön</Link>}>
        Aradığın sayfa taşınmış ya da hiç var olmamış olabilir.
      </EmptyState>
    </div>
  )
}
