import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Coffee, RotateCcw } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { ordersApi, queryKeys } from '../api/endpoints'
import { Alert, EmptyState, ErrorState, Loading } from '../components/StateViews'
import { ACTIVE_ORDER, ORDER_STATUS, SIZES, formatDateTime, labelOf } from '../lib/format'

const STATUS_BADGE = {
  COMPLETED: 'badge--open',
  CANCELLED: 'badge--closed',
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const historyQuery = useQuery({
    queryKey: queryKeys.orders,
    queryFn: () => ordersApi.history({ limit: 50 }),
  })

  const reorder = useMutation({
    mutationFn: ordersApi.reorder,
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orders })
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription })
      navigate(`/siparis/${order.id}`)
    },
  })

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Siparişlerim</h1>
          <p className="muted">Devam eden siparişlerini takip et, favorilerini tek dokunuşla tekrarla.</p>
        </div>
      </div>

      {reorder.isError && <div style={{ marginBottom: 16 }}><Alert>{reorder.error.message}</Alert></div>}
      {historyQuery.isLoading && <Loading />}
      {historyQuery.isError && <ErrorState error={historyQuery.error} onRetry={historyQuery.refetch} />}
      {historyQuery.isSuccess && historyQuery.data.items.length === 0 && (
        <EmptyState icon={Coffee} title="Henüz siparişin yok"
          action={<Link to="/" className="btn btn--primary btn--sm">Dükkân keşfet</Link>}>
          İlk kahveni sipariş ettiğinde burada görünecek.
        </EmptyState>
      )}

      <div className="stack-sm">
        {historyQuery.data?.items.map((order) => {
          const item = order.items[0]
          const active = ACTIVE_ORDER.includes(order.status)
          return (
            <div key={order.id} className="card history-item">
              <div className="history-item__icon"><Coffee size={22} /></div>
              <Link to={`/siparis/${order.id}`} className="history-item__body">
                <div className="row wrap" style={{ gap: 8 }}>
                  <h3>{item.product_name}</h3>
                  <span className={`badge ${STATUS_BADGE[order.status] ?? 'badge--yellow'}`}>
                    {ORDER_STATUS[order.status].label}
                  </span>
                </div>
                <p className="subtle">
                  {order.shop.name} · {labelOf(SIZES, item.size)} · {formatDateTime(order.created_at)}
                </p>
              </Link>
              <div className="history-item__actions">
                {active ? (
                  <Link to={`/siparis/${order.id}`} className="btn btn--dark btn--sm">QR'ı göster</Link>
                ) : (
                  <button type="button" className="btn btn--ghost btn--sm" disabled={reorder.isPending}
                    onClick={() => reorder.mutate(order.id)}>
                    <RotateCcw size={15} /> Tekrarla
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
