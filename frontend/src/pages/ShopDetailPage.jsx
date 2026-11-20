import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, MapPin, Phone, Star } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { queryKeys, shopsApi } from '../api/endpoints'
import ShopMap from '../components/ShopMap'
import { Alert, ErrorState, Loading } from '../components/StateViews'
import { useSubscription } from '../hooks/useSubscription'
import { useUserLocation } from '../hooks/useUserLocation'
import { CATEGORY_LABELS, formatDistance, formatTime, formatTL } from '../lib/format'

function groupByCategory(menu) {
  const groups = new Map()
  for (const product of menu) {
    if (!groups.has(product.category)) groups.set(product.category, [])
    groups.get(product.category).push(product)
  }
  return [...groups.entries()]
}

export default function ShopDetailPage() {
  const { shopId } = useParams()
  const { position, status } = useUserLocation()
  const params = status === 'granted' ? { lat: position.lat, lng: position.lng } : {}
  const shopQuery = useQuery({
    queryKey: queryKeys.shop(shopId, params),
    queryFn: () => shopsApi.get(shopId, params),
    enabled: status !== 'loading',
  })
  const { data: subscription } = useSubscription()

  if (shopQuery.isLoading || status === 'loading') return <Loading label="Dükkân yükleniyor…" />
  if (shopQuery.isError) {
    return (
      <div className="page">
        <ErrorState error={shopQuery.error} onRetry={shopQuery.refetch} />
      </div>
    )
  }

  const shop = shopQuery.data
  const canOrder = shop.is_open_now && Boolean(subscription)

  return (
    <div className="page stack" style={{ gap: 28 }}>
      <div>
        <Link to="/" className="back-link">
          <ArrowLeft size={16} /> Dükkânlar
        </Link>
        <div className="shop-hero">
          <div className="card card--hero">
            <div className="row-between">
              <span className={`badge ${shop.is_open_now ? 'badge--open' : 'badge--closed'}`}>
                {shop.is_open_now ? 'Şu an açık' : 'Şu an kapalı'}
              </span>
              <span className="row" style={{ gap: 6 }}>
                <Star size={16} fill="var(--yellow-500)" color="var(--yellow-500)" />
                <strong>{shop.rating.toFixed(1)}</strong>
                <span className="muted">({shop.rating_count})</span>
              </span>
            </div>
            <h1 style={{ marginTop: 16 }}>{shop.name}</h1>
            <div className="shop-hero__facts muted">
              <span><MapPin size={16} /> {shop.address}</span>
              <span><Clock size={16} /> {formatTime(shop.opens_at)} – {formatTime(shop.closes_at)}</span>
              {shop.distance_km != null && <span>📍 {formatDistance(shop.distance_km)} uzaklıkta</span>}
              {shop.phone && <span><Phone size={16} /> {shop.phone}</span>}
            </div>
          </div>
          <div className="shop-hero__map">
            <ShopMap shops={[shop]} interactive={false} />
          </div>
        </div>
      </div>

      {!shop.is_open_now && <Alert variant="warning">Dükkân şu an kapalı; menüye göz atabilir, açılınca sipariş verebilirsin.</Alert>}
      {shop.is_open_now && !subscription && (
        <Alert variant="info">
          Sipariş vermek için bir paket seçmelisin. <Link to="/abonelik"><strong>Paketlere göz at →</strong></Link>
        </Alert>
      )}

      <section className="stack" style={{ gap: 28 }}>
        <h2>Menü</h2>
        {groupByCategory(shop.menu).map(([category, products]) => (
          <div key={category} className="menu-group">
            <h3>{CATEGORY_LABELS[category] ?? category}</h3>
            <div className="menu-grid">
              {products.map((product) => (
                <div key={product.id} className="card product">
                  <div className="stack-sm">
                    <div className="row-between">
                      <h3>{product.name}</h3>
                      {!product.is_available && <span className="badge badge--closed">Tükendi</span>}
                    </div>
                    {product.description && <p className="subtle">{product.description}</p>}
                  </div>
                  <div className="row-between">
                    <span className="product__price">
                      {subscription ? (
                        <>
                          <s>{formatTL(product.price_kurus)}</s>
                          <span className="badge badge--yellow">Pakete dahil</span>
                        </>
                      ) : (
                        formatTL(product.price_kurus)
                      )}
                    </span>
                    {canOrder && product.is_available ? (
                      <Link to={`/dukkan/${shop.id}/siparis/${product.id}`} className="btn btn--dark btn--sm">
                        Seç
                      </Link>
                    ) : (
                      <button type="button" className="btn btn--dark btn--sm" disabled>
                        Seç
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
