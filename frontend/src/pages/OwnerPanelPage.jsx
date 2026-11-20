import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BellRing, CheckCircle2, Coffee, QrCode, ShieldAlert, ShieldCheck, Timer, TrendingUp } from 'lucide-react'
import { useCallback, useState } from 'react'

import { ordersApi, queryKeys } from '../api/endpoints'
import OrderCard from '../components/OrderCard'
import QrScanner from '../components/QrScanner'
import { Alert, EmptyState, ErrorState, Loading } from '../components/StateViews'
import { useEventStream } from '../hooks/useEventStream'
import { ORDER_STATUS } from '../lib/format'

const COLUMNS = ['PENDING', 'ACCEPTED', 'PREPARING', 'READY']
const COLUMN_TITLES = { PENDING: 'Yeni', ACCEPTED: 'Kabul edildi', PREPARING: 'Hazırlanıyor', READY: 'Teslime hazır' }

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="card stat-card">
      <span className="stat-card__icon"><Icon size={20} /></span>
      <div>
        <p className="subtle">{label}</p>
        <strong className="stat-card__value">{value}</strong>
      </div>
    </div>
  )
}

function HourlyChart({ hourly }) {
  const hours = hourly.map((count, hour) => ({ hour, count })).slice(7, 24) // 07:00–23:00
  const max = Math.max(1, ...hours.map((h) => h.count))
  return (
    <figure className="hourly" aria-label="Saatlik sipariş dağılımı">
      {hours.map(({ hour, count }) => (
        <div key={hour} className="hourly__bar" title={`${hour}:00 — ${count} sipariş`}>
          <span style={{ height: `${(count / max) * 100}%` }} />
          <small>{hour}</small>
        </div>
      ))}
    </figure>
  )
}

/** QR okutulduktan sonra: doğrulama sonucu ve teslim düğmesi. */
function ScanResult({ result, error, delivering, onDeliver, onRetry }) {
  if (error) {
    const fake = error.code === 'QR_SIGNATURE_INVALID'
    return (
      <div className="stack-sm">
        <Alert icon={ShieldAlert}>
          <strong>{fake ? 'Sahte veya değiştirilmiş QR!' : 'QR kabul edilmedi'}</strong>
          <br />
          {error.message}
        </Alert>
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>Tekrar okut</button>
      </div>
    )
  }
  if (!result) return null
  const item = result.order.items[0]
  return (
    <div className="stack-sm">
      <Alert variant="success" icon={ShieldCheck}>
        <strong>QR gerçek.</strong> {result.message}
      </Alert>
      <div className="card" style={{ padding: 14 }}>
        <strong>{item.product_name}</strong> · {result.order.customer_name}
        <p className="subtle">Durum: {ORDER_STATUS[result.order.status].label}</p>
      </div>
      {result.can_complete ? (
        <button type="button" className="btn btn--primary" disabled={delivering} onClick={onDeliver}>
          <CheckCircle2 size={18} /> {delivering ? 'Teslim ediliyor…' : 'Teslim et'}
        </button>
      ) : (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>Başka QR okut</button>
      )}
    </div>
  )
}

export default function OwnerPanelPage() {
  const queryClient = useQueryClient()
  const [scannerOpen, setScannerOpen] = useState(false)
  const [scanAttempt, setScanAttempt] = useState(0) // yeniden okutmada kamera sıfırdan başlasın
  const [scan, setScan] = useState({ content: null, result: null, error: null })
  const [notice, setNotice] = useState(null)

  const incomingQuery = useQuery({
    queryKey: queryKeys.incoming,
    queryFn: () => ordersApi.incoming({ limit: 100 }),
    refetchInterval: 30_000, // canlı bağlantı koparsa yedek
  })
  const statsQuery = useQuery({ queryKey: queryKeys.stats, queryFn: () => ordersApi.stats() })

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKeys.incoming })
    queryClient.invalidateQueries({ queryKey: queryKeys.stats })
  }, [queryClient])

  // Canlı bildirim: yeni sipariş gelince ya da durum değişince listeyi anında tazele.
  useEventStream('/orders/incoming/events', (event) => {
    refresh()
    if (event.type === 'order.created') setNotice('Yeni sipariş geldi!')
  })

  const advance = useMutation({
    mutationFn: ({ orderId, status, qrContent }) => ordersApi.updateStatus(orderId, status, qrContent),
    onSuccess: refresh,
  })

  const verify = useMutation({
    mutationFn: ordersApi.verifyQr,
    onSuccess: (result) => setScan((s) => ({ ...s, result, error: null })),
    onError: (error) => setScan((s) => ({ ...s, result: null, error })),
  })

  const handleScanned = useCallback(
    (content) => {
      setScan({ content, result: null, error: null })
      verify.mutate(content)
    },
    // verify.mutate kararlı bir fonksiyondur
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  function openScanner() {
    setScan({ content: null, result: null, error: null })
    setScanAttempt((n) => n + 1)
    setScannerOpen(true)
  }

  function deliver() {
    advance.mutate(
      { orderId: scan.result.order.id, status: 'COMPLETED', qrContent: scan.content },
      {
        onSuccess: () => {
          setScannerOpen(false)
          setNotice('Sipariş teslim edildi. Afiyet olsun!')
        },
      },
    )
  }

  function handleAdvance(order, next) {
    if (next.needsQr) return openScanner()
    advance.mutate({ orderId: order.id, status: next.status })
  }

  function handleReject(order) {
    if (window.confirm('Siparişi reddetmek istiyor musun? Müşterinin kahve hakkı iade edilir.')) {
      advance.mutate({ orderId: order.id, status: 'CANCELLED' })
    }
  }

  const orders = incomingQuery.data?.items ?? []
  const stats = statsQuery.data

  return (
    <div className="page stack" style={{ gap: 24 }}>
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Dükkân paneli</h1>
          <p className="muted">Siparişler canlı olarak gelir; teslimde müşterinin QR kodunu okut.</p>
        </div>
        <button type="button" className="btn btn--primary" onClick={openScanner}>
          <QrCode size={18} /> QR okut
        </button>
      </div>

      <div aria-live="polite">
        {notice && (
          <Alert variant="success" icon={BellRing}>
            {notice}{' '}
            <button type="button" className="link-btn" onClick={() => setNotice(null)}>Tamam</button>
          </Alert>
        )}
      </div>
      {advance.isError && <Alert>{advance.error.message}</Alert>}

      {stats && (
        <section className="stack-sm" aria-label="Bugünün özeti">
          <div className="stats-grid">
            <StatCard icon={Coffee} label="Bugünkü sipariş" value={stats.total_orders} />
            <StatCard icon={BellRing} label="Bekleyen" value={stats.active} />
            <StatCard icon={CheckCircle2} label="Teslim edilen" value={stats.completed} />
            <StatCard icon={Timer} label="Ort. hazırlama" value={stats.avg_prep_minutes != null ? `${stats.avg_prep_minutes} dk` : '—'} />
          </div>
          <div className="stats-detail">
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Saatlik yoğunluk</h3>
              <HourlyChart hourly={stats.hourly} />
            </div>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}><TrendingUp size={16} /> En çok satanlar</h3>
              {stats.top_products.length === 0 ? (
                <p className="subtle">Bugün henüz satış yok.</p>
              ) : (
                <ol className="top-products">
                  {stats.top_products.map((p) => (
                    <li key={p.name}><span>{p.name}</span><strong>{p.count}</strong></li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </section>
      )}

      {incomingQuery.isLoading && <Loading label="Siparişler yükleniyor…" />}
      {incomingQuery.isError && <ErrorState error={incomingQuery.error} onRetry={incomingQuery.refetch} />}
      {incomingQuery.isSuccess && orders.length === 0 && (
        <EmptyState icon={Coffee} title="Şu an bekleyen sipariş yok">Yeni sipariş gelince burada anında görünecek.</EmptyState>
      )}
      {orders.length > 0 && (
        <section className="board" aria-label="Siparişler">
          {COLUMNS.map((status) => {
            const columnOrders = orders.filter((order) => order.status === status)
            return (
              <div key={status} className="board__column">
                <h2 className="board__title">
                  {COLUMN_TITLES[status]} <span className="badge badge--navy">{columnOrders.length}</span>
                </h2>
                {columnOrders.map((order) => (
                  <OrderCard key={order.id} order={order} busy={advance.isPending}
                    onAdvance={handleAdvance} onReject={handleReject} />
                ))}
              </div>
            )
          })}
        </section>
      )}

      {scannerOpen && (
        <QrScanner key={scanAttempt} onResult={handleScanned} onClose={() => setScannerOpen(false)}>
          {verify.isPending && <Loading label="Doğrulanıyor…" />}
          <ScanResult
            result={scan.result}
            error={scan.error}
            delivering={advance.isPending}
            onDeliver={deliver}
            onRetry={openScanner}
          />
        </QrScanner>
      )}
    </div>
  )
}
