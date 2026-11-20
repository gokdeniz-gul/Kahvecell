import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Coffee, Minus, Plus, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ordersApi, queryKeys, shopsApi } from '../api/endpoints'
import { Alert, ErrorState, Loading } from '../components/StateViews'
import { useSubscription } from '../hooks/useSubscription'
import { ALLERGENS, MILKS, SIZES, SUGARS, allergenConflicts, formatTL, labelOf } from '../lib/format'
import { useAuthStore } from '../store/authStore'

function Segmented({ options, value, onChange, label }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export default function OrderPage() {
  const { shopId, productId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [choice, setChoice] = useState({ size: 'M', sugar: 'NONE', milk: 'NONE', extra_shots: 0, note: '' })
  const set = (field) => (value) => setChoice((current) => ({ ...current, [field]: value }))

  const shopQuery = useQuery({ queryKey: queryKeys.shop(shopId, {}), queryFn: () => shopsApi.get(shopId) })
  const { data: subscription, isLoading: subLoading } = useSubscription()
  const userAllergens = useAuthStore((state) => state.user?.preferences?.allergens)
  const conflicts = allergenConflicts(choice.milk, userAllergens)

  const createOrder = useMutation({
    mutationFn: () =>
      ordersApi.create({
        shop_id: shopId,
        product_id: productId,
        ...choice,
        note: choice.note.trim() || null,
      }),
    onSuccess: (order) => {
      // Kalan hak ve geçmiş değişti: bu verileri bir sonraki gösterimde tazele.
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription })
      queryClient.invalidateQueries({ queryKey: queryKeys.orders })
      navigate(`/siparis/${order.id}`, { replace: true })
    },
  })

  if (shopQuery.isLoading || subLoading) return <Loading />
  if (shopQuery.isError) return <div className="page"><ErrorState error={shopQuery.error} onRetry={shopQuery.refetch} /></div>

  const shop = shopQuery.data
  const product = shop.menu.find((item) => item.id === productId)
  if (!product) {
    return <div className="page"><ErrorState error={{ message: 'Ürün bu dükkânın menüsünde bulunamadı.' }} /></div>
  }

  const credits = subscription?.remaining_credits
  const outOfCredits = credits === 0
  const blocked = !subscription || outOfCredits || !shop.is_open_now || !product.is_available

  return (
    <div className="page">
      <Link to={`/dukkan/${shop.id}`} className="back-link">
        <ArrowLeft size={16} /> {shop.name}
      </Link>
      <div className="page-head">
        <div>
          <h1>{product.name}</h1>
          <p className="muted">{product.description}</p>
        </div>
      </div>

      <div className="order-layout">
        <div className="card stack" style={{ gap: 24 }}>
          <div className="field">
            <label>Boy</label>
            <Segmented label="Boy" options={SIZES} value={choice.size} onChange={set('size')} />
          </div>
          <div className="field">
            <label>Şeker</label>
            <Segmented label="Şeker" options={SUGARS} value={choice.sugar} onChange={set('sugar')} />
          </div>
          <div className="field">
            <label>Süt</label>
            <Segmented label="Süt" options={MILKS} value={choice.milk} onChange={set('milk')} />
          </div>
          <div className="field">
            <label>Ek espresso shot</label>
            <div className="stepper">
              <button type="button" aria-label="Azalt" disabled={choice.extra_shots === 0}
                onClick={() => set('extra_shots')(choice.extra_shots - 1)}>
                <Minus size={16} />
              </button>
              <output aria-live="polite">{choice.extra_shots}</output>
              <button type="button" aria-label="Artır" disabled={choice.extra_shots === 3}
                onClick={() => set('extra_shots')(choice.extra_shots + 1)}>
                <Plus size={16} />
              </button>
              <span className="subtle">en fazla 3</span>
            </div>
          </div>
          <div className="field">
            <label htmlFor="note">Barista'ya not</label>
            <textarea id="note" className="input" maxLength={200} placeholder="Örn. az köpüklü lütfen"
              value={choice.note} onChange={(e) => set('note')(e.target.value)} />
            <span className="field__hint">{choice.note.length}/200</span>
          </div>
        </div>

        <aside className="card order-summary stack">
          <div className="row">
            <div className="shop-card__thumb" style={{ width: 52, height: 52 }}><Coffee size={24} /></div>
            <div>
              <h3>{product.name}</h3>
              <p className="subtle">{shop.name}</p>
            </div>
          </div>
          <div>
            <div className="summary-line"><span className="muted">Boy</span><span>{labelOf(SIZES, choice.size)}</span></div>
            <div className="summary-line"><span className="muted">Şeker</span><span>{labelOf(SUGARS, choice.sugar)}</span></div>
            <div className="summary-line"><span className="muted">Süt</span><span>{labelOf(MILKS, choice.milk)}</span></div>
            <div className="summary-line"><span className="muted">Ek shot</span><span>{choice.extra_shots}</span></div>
            <div className="summary-line">
              <span className="muted">Menü fiyatı</span>
              <span><s className="subtle">{formatTL(product.price_kurus)}</s> <strong>Pakete dahil</strong></span>
            </div>
          </div>

          {subscription && (
            <Alert variant="info" icon={Coffee}>
              {credits == null
                ? 'Sınırsız paketindesin, hakkından bir şey düşmez.'
                : `Bu siparişle 1 kahve hakkın kullanılacak (kalan: ${credits}).`}
            </Alert>
          )}
          {!subscription && (
            <Alert variant="warning">
              Sipariş için aktif bir paketin olmalı. <Link to="/abonelik"><strong>Paket seç →</strong></Link>
            </Alert>
          )}
          {outOfCredits && (
            <Alert variant="warning">
              Bu ayki kahve hakkın bitti. <Link to="/abonelik"><strong>Paketini yükselt →</strong></Link>
            </Alert>
          )}
          {conflicts.length > 0 && (
            <Alert variant="warning" icon={ShieldAlert}>
              <strong>Alerjen uyarısı:</strong> {labelOf(MILKS, choice.milk)} süt{' '}
              {conflicts.map((a) => labelOf(ALLERGENS, a).toLocaleLowerCase('tr-TR')).join(', ')} içerebilir.
              Profilinde bu alerjen işaretli. Başka bir süt seçebilirsin.
            </Alert>
          )}
          {!shop.is_open_now && <Alert variant="warning">Dükkân şu an kapalı.</Alert>}
          {createOrder.isError && <Alert>{createOrder.error.message}</Alert>}

          <button type="button" className="btn btn--primary btn--block" disabled={blocked || createOrder.isPending}
            onClick={() => createOrder.mutate()}>
            {createOrder.isPending ? 'Sipariş veriliyor…' : 'Siparişi onayla'}
          </button>
        </aside>
      </div>
    </div>
  )
}
