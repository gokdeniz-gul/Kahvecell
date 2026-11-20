import { Clock, Zap } from 'lucide-react'

import { MILKS, NEXT_ACTION, SIZES, SUGARS, formatClock, labelOf } from '../lib/format'

function customization(item) {
  return [
    labelOf(SIZES, item.size),
    item.milk !== 'NONE' && `${labelOf(MILKS, item.milk)} süt`,
    item.sugar !== 'NONE' && `${labelOf(SUGARS, item.sugar)} şeker`,
    item.extra_shots > 0 && `+${item.extra_shots} shot`,
  ]
    .filter(Boolean)
    .join(' · ')
}

export default function OrderCard({ order, busy, onAdvance, onReject }) {
  const item = order.items[0]
  const next = NEXT_ACTION[order.status]
  const canReject = order.allowed_next_statuses.includes('CANCELLED')

  return (
    <article className={`card order-card${order.is_priority ? ' order-card--priority' : ''}`} aria-label={`${item.product_name} siparişi`}>
      <div className="row-between">
        <h3>{item.product_name}</h3>
        {order.is_priority && <span className="badge badge--yellow"><Zap size={12} /> Öncelikli</span>}
      </div>
      <p className="subtle">{customization(item)}</p>
      {order.note && <p className="order-card__note">“{order.note}”</p>}
      <div className="row-between subtle">
        <span>{order.customer_name}</span>
        <span className="row" style={{ gap: 4 }}><Clock size={13} /> {formatClock(order.created_at)}</span>
      </div>
      <p className="subtle">{order.shop.name}</p>
      <div className="row">
        {next && (
          <button type="button" className={`btn btn--sm ${next.needsQr ? 'btn--primary' : 'btn--dark'}`} style={{ flex: 1 }}
            disabled={busy} onClick={() => onAdvance(order, next)}>
            {next.label}
          </button>
        )}
        {canReject && (
          <button type="button" className="btn btn--danger btn--sm" disabled={busy} onClick={() => onReject(order)}>
            Reddet
          </button>
        )}
      </div>
    </article>
  )
}
