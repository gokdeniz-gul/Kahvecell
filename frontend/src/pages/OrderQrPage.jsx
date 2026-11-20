import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, CircleX, Copy, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ordersApi, queryKeys } from '../api/endpoints'
import { Alert, ErrorState, Loading } from '../components/StateViews'
import { useEventStream } from '../hooks/useEventStream'
import {
  ACTIVE_ORDER,
  MILKS,
  ORDER_FLOW,
  ORDER_STATUS,
  SIZES,
  SUGARS,
  formatDateTime,
  labelOf,
} from '../lib/format'

function StatusTimeline({ status }) {
  const currentIndex = ORDER_FLOW.indexOf(status)
  return (
    <ol className="timeline">
      {ORDER_FLOW.map((step, index) => {
        const state = index < currentIndex || status === 'COMPLETED' ? 'done' : index === currentIndex ? 'current' : ''
        return (
          <li key={step} className={state}>
            <span className="timeline__dot">{state === 'done' ? <Check size={16} /> : index + 1}</span>
            <span className="timeline__label">
              <strong>{ORDER_STATUS[step].label}</strong>
              {state === 'current' && <span className="subtle">{ORDER_STATUS[step].hint}</span>}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export default function OrderQrPage() {
  const { orderId } = useParams()
  const queryClient = useQueryClient()

  const orderQuery = useQuery({
    queryKey: queryKeys.order(orderId),
    queryFn: () => ordersApi.get(orderId),
    // Asıl güncelleme canlı bağlantıdan (SSE) gelir; bağlantı koparsa 30 sn'de bir yedek kontrol.
    refetchInterval: (query) => (ACTIVE_ORDER.includes(query.state.data?.status) ? 30_000 : false),
  })

  const isActive = ACTIVE_ORDER.includes(orderQuery.data?.status)
  // Dükkân durumu değiştirdiği anda sunucu haber verir; siparişi tazeleriz.
  useEventStream(`/orders/${orderId}/events`, () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.order(orderId) })
    queryClient.invalidateQueries({ queryKey: queryKeys.orders })
  }, { enabled: isActive })

  const [copied, setCopied] = useState(false)
  async function copyQrContent(content) {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  const cancelOrder = useMutation({
    mutationFn: () => ordersApi.cancel(orderId),
    onSuccess: (order) => {
      queryClient.setQueryData(queryKeys.order(orderId), order)
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription })
      queryClient.invalidateQueries({ queryKey: queryKeys.orders })
    },
  })

  if (orderQuery.isLoading) return <Loading label="Sipariş yükleniyor…" />
  if (orderQuery.isError) return <div className="page"><ErrorState error={orderQuery.error} onRetry={orderQuery.refetch} /></div>

  const order = orderQuery.data
  const item = order.items[0]
  const canCancel = order.allowed_next_statuses.includes('CANCELLED')

  return (
    <div className="page">
      <Link to="/gecmis" className="back-link">
        <ArrowLeft size={16} /> Siparişlerim
      </Link>
      <div className="page-head">
        <div>
          <h1 aria-live="polite">{ORDER_STATUS[order.status].label}</h1>
          <p className="muted">{order.shop.name} · {formatDateTime(order.created_at)}</p>
        </div>
        {order.is_priority && <span className="badge badge--yellow">⚡ Öncelikli sipariş</span>}
      </div>

      <div className="qr-layout">
        <div className="card qr-card">
          {order.qr ? (
            <>
              <div className="qr-frame">
                <img src={order.qr.image_data_url} alt="Sipariş teslim QR kodu" />
              </div>
              <div className="stack-sm">
                <h2>Kasada bu kodu okut</h2>
                <p className="muted">Kod sana özel ve imzalı; ekran görüntüsü başka siparişte işe yaramaz.</p>
              </div>
              <span className="badge badge--navy"><ShieldCheck size={14} /> HMAC-SHA256 ile imzalı</span>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => copyQrContent(order.qr.content)}>
                <Copy size={15} /> {copied ? 'Kopyalandı' : 'QR içeriğini kopyala'}
              </button>
            </>
          ) : order.status === 'COMPLETED' ? (
            <div className="state">
              <div className="state__icon" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}><Check size={32} /></div>
              <h3>Teslim edildi</h3>
              <p>{order.completed_at && formatDateTime(order.completed_at)} · Afiyet olsun!</p>
            </div>
          ) : (
            <div className="state">
              <div className="state__icon"><CircleX size={32} /></div>
              <h3>Sipariş iptal edildi</h3>
              <p>{order.credits_used ? 'Kahve hakkın iade edildi.' : ''}</p>
            </div>
          )}
        </div>

        <div className="stack">
          <div className="card">
            {order.status === 'CANCELLED' ? (
              <p className="muted">Bu sipariş iptal edildi.</p>
            ) : (
              <StatusTimeline status={order.status} />
            )}
          </div>

          <div className="card stack-sm">
            <h3>{item.product_name}</h3>
            <div className="summary-line"><span className="muted">Boy</span><span>{labelOf(SIZES, item.size)}</span></div>
            <div className="summary-line"><span className="muted">Şeker</span><span>{labelOf(SUGARS, item.sugar)}</span></div>
            <div className="summary-line"><span className="muted">Süt</span><span>{labelOf(MILKS, item.milk)}</span></div>
            <div className="summary-line"><span className="muted">Ek shot</span><span>{item.extra_shots}</span></div>
            {order.note && <div className="summary-line"><span className="muted">Not</span><span>{order.note}</span></div>}
            <div className="summary-line"><span className="muted">Kullanılan hak</span><span>{order.credits_used || 'Sınırsız paket'}</span></div>
          </div>

          {cancelOrder.isError && <Alert>{cancelOrder.error.message}</Alert>}
          {canCancel && (
            <button type="button" className="btn btn--danger" disabled={cancelOrder.isPending}
              onClick={() => window.confirm('Siparişi iptal etmek istiyor musun? Kahve hakkın iade edilir.') && cancelOrder.mutate()}>
              {cancelOrder.isPending ? 'İptal ediliyor…' : 'Siparişi iptal et'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
