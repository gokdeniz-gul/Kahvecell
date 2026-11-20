import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Coffee, Crown, MapPin, Search, Star } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { queryKeys, shopsApi } from '../api/endpoints'
import ShopMap from '../components/ShopMap'
import { EmptyState, ErrorState } from '../components/StateViews'
import { useSubscription } from '../hooks/useSubscription'
import { useUserLocation } from '../hooks/useUserLocation'
import { formatDistance, formatTime } from '../lib/format'
import { useAuthStore } from '../store/authStore'

function SubscriptionBanner() {
  const { data: subscription, isLoading } = useSubscription()
  if (isLoading) return null

  if (!subscription) {
    return (
      <Link to="/abonelik" className="card card--hero sub-banner">
        <div>
          <strong>Henüz bir paketin yok</strong>
          <p className="muted">89,99 TL'den başlayan paketlerle sipariş vermeye başla.</p>
        </div>
        <span className="btn btn--primary btn--sm">Paketler</span>
      </Link>
    )
  }
  const credits = subscription.remaining_credits
  return (
    <Link to="/abonelik" className="card card--hero sub-banner">
      <div className="row">
        <Crown size={22} color="var(--yellow-500)" />
        <div>
          <strong>{subscription.plan.name} paketi</strong>
          <p className="muted">{credits == null ? 'Sınırsız kahve' : `${credits} kahve hakkın kaldı`}</p>
        </div>
      </div>
      <ChevronRight size={20} />
    </Link>
  )
}

function ShopCard({ shop, active, onHover }) {
  return (
    <Link
      to={`/dukkan/${shop.id}`}
      className={`card card--interactive shop-card${active ? ' card--selected' : ''}`}
      onMouseEnter={() => onHover(shop.id)}
    >
      <div className="shop-card__thumb">
        <Coffee size={28} />
      </div>
      <div className="shop-card__body">
        <div className="row-between">
          <h3>{shop.name}</h3>
          <span className={`badge ${shop.is_open_now ? 'badge--open' : 'badge--closed'}`}>
            {shop.is_open_now ? 'Açık' : 'Kapalı'}
          </span>
        </div>
        <p className="subtle" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {shop.address}
        </p>
        <div className="shop-card__meta">
          <span><Star size={14} fill="var(--yellow-500)" color="var(--yellow-500)" /> {shop.rating.toFixed(1)}</span>
          {shop.distance_km != null && <span><MapPin size={14} /> {formatDistance(shop.distance_km)}</span>}
          <span>{formatTime(shop.opens_at)}–{formatTime(shop.closes_at)}</span>
        </div>
      </div>
    </Link>
  )
}

export default function HomePage() {
  const user = useAuthStore((state) => state.user)
  const navigate = useNavigate()
  const { position, status: locationStatus } = useUserLocation()
  const [search, setSearch] = useState('')
  const [openNow, setOpenNow] = useState(false)
  const [activeShopId, setActiveShopId] = useState(null)

  // Her tuşta istek atmamak için arama metni bir adım geriden gelir.
  const deferredSearch = useDeferredValue(search.trim())
  const params = {
    lat: position.lat,
    lng: position.lng,
    ...(deferredSearch && { q: deferredSearch }),
    ...(openNow && { open_now: true }),
  }
  const shopsQuery = useQuery({
    queryKey: queryKeys.shops(params),
    queryFn: () => shopsApi.list(params),
    enabled: locationStatus !== 'loading',
    placeholderData: (previous) => previous, // filtre değişirken liste boşalmasın
  })
  const shops = shopsQuery.data?.items ?? []
  const firstName = user?.full_name?.split(' ')[0]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Merhaba{firstName ? `, ${firstName}` : ''} 👋</h1>
          <p className="muted">
            {locationStatus === 'granted'
              ? 'Sana en yakın dükkânlar listeleniyor.'
              : `Konum izni olmadığı için ${position.label ?? 'varsayılan konuma'} göre gösteriliyor.`}
          </p>
        </div>
      </div>

      <div className="discover">
        <div className="discover__list">
          <SubscriptionBanner />

          <div className="search">
            <Search size={18} />
            <input
              className="input"
              type="search"
              placeholder="Dükkân, semt veya adres ara"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Dükkân ara"
            />
          </div>
          <div className="row wrap">
            <button type="button" className="toggle" aria-pressed={openNow} onClick={() => setOpenNow(!openNow)}>
              ● Şu an açık
            </button>
            {shopsQuery.data && <span className="subtle">{shopsQuery.data.total} dükkân</span>}
          </div>

          {(shopsQuery.isLoading || locationStatus === 'loading') &&
            [1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 92 }} />)}
          {shopsQuery.isError && <ErrorState error={shopsQuery.error} onRetry={shopsQuery.refetch} />}
          {shopsQuery.isSuccess && shops.length === 0 && (
            <EmptyState icon={Search} title="Dükkân bulunamadı">
              Farklı bir arama dene ya da filtreyi kaldır.
            </EmptyState>
          )}
          {shops.map((shop) => (
            <ShopCard key={shop.id} shop={shop} active={shop.id === activeShopId} onHover={setActiveShopId} />
          ))}
        </div>

        <div className="discover__map">
          <ShopMap
            shops={shops}
            userPosition={locationStatus === 'granted' ? position : null}
            activeShopId={activeShopId}
            onSelect={(id) => (id === activeShopId ? navigate(`/dukkan/${id}`) : setActiveShopId(id))}
          />
        </div>
      </div>
    </div>
  )
}
