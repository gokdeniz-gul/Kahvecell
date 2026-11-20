import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, CheckCircle2, CreditCard, Crown, Lock, X } from 'lucide-react'
import { useState } from 'react'

import { paymentsApi, queryKeys, subscriptionsApi } from '../api/endpoints'
import { Alert, ErrorState, Loading } from '../components/StateViews'
import { useSubscription } from '../hooks/useSubscription'
import { formatDate, formatDateTime, formatTL } from '../lib/format'

const TEST_CARDS = [
  { number: '4242 4242 4242 4242', label: '4242… başarılı' },
  { number: '4000 0000 0000 0002', label: '4000…0002 reddedilir' },
]

const PLAN_PERKS = {
  STARTER: ['Ayda 10 kahve', 'Tüm anlaşmalı dükkânlar'],
  PREMIUM: ['Ayda 20 kahve', 'Tüm anlaşmalı dükkânlar', '2 misafir hakkı'],
  UNLIMITED: ['Sınırsız kahve', 'Tüm anlaşmalı dükkânlar', '5 misafir hakkı', 'Öncelikli hazırlanma'],
}

const formatCardNumber = (value) => value.replace(/\D/g, '').slice(0, 16).replace(/(\d{4})(?=\d)/g, '$1 ')

/** Kart formu doğrulaması (client-side). Sunucu da ayrıca doğrular. */
function validateCard(card) {
  const errors = {}
  if (card.holder.trim().length < 2) errors.holder = 'Kart üzerindeki ismi gir.'
  if (card.number.replace(/\s/g, '').length !== 16) errors.number = 'Kart numarası 16 haneli olmalı.'
  const match = card.expiry.match(/^(\d{2})\/(\d{2})$/)
  if (!match || Number(match[1]) < 1 || Number(match[1]) > 12) {
    errors.expiry = 'AA/YY biçiminde gir.'
  } else {
    const now = new Date()
    const [month, year] = [Number(match[1]), 2000 + Number(match[2])]
    if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) {
      errors.expiry = 'Kartın süresi dolmuş.'
    }
  }
  if (!/^\d{3,4}$/.test(card.cvc)) errors.cvc = '3 haneli güvenlik kodu.'
  return errors
}

function PaymentPanel({ checkout, onClose, onPaid }) {
  const [card, setCard] = useState({ holder: '', number: '', expiry: '', cvc: '' })
  const [errors, setErrors] = useState({})
  const update = (field) => (event) => {
    let value = event.target.value
    if (field === 'number') value = formatCardNumber(value)
    if (field === 'expiry') value = value.replace(/\D/g, '').slice(0, 4).replace(/^(\d{2})(\d)/, '$1/$2')
    if (field === 'cvc') value = value.replace(/\D/g, '').slice(0, 4)
    setCard((current) => ({ ...current, [field]: value }))
  }

  const pay = useMutation({
    mutationFn: async () => {
      const [month, year] = card.expiry.split('/')
      const payment = await paymentsApi.process(checkout.plan.plan_type, {
        card_holder: card.holder.trim(),
        card_number: card.number,
        expiry_month: Number(month),
        expiry_year: 2000 + Number(year),
        cvc: card.cvc,
      })
      // Ödeme başarılı: transaction_id ile aboneliği başlat / yükselt.
      return checkout.mode === 'start'
        ? subscriptionsApi.start(checkout.plan.plan_type, payment.transaction_id)
        : subscriptionsApi.changePlan(checkout.plan.plan_type, payment.transaction_id)
    },
    onSuccess: onPaid,
  })

  function submit(event) {
    event.preventDefault()
    const found = validateCard(card)
    setErrors(found)
    if (Object.keys(found).length === 0) pay.mutate()
  }

  const fieldClass = (name) => `input${errors[name] ? ' input--invalid' : ''}`

  return (
    <form className="card pay-panel stack" onSubmit={submit} noValidate>
      <div className="row-between">
        <div>
          <h2>{checkout.mode === 'start' ? `${checkout.plan.name} paketini al` : `${checkout.plan.name} paketine yükselt`}</h2>
          <p className="muted">
            Ödenecek tutar: <strong>{formatTL(checkout.amount)}</strong>
            {checkout.mode === 'upgrade' && ' (sadece fiyat farkı)'}
          </p>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Kapat"><X size={20} /></button>
      </div>

      <div className="field">
        <label htmlFor="holder">Kart üzerindeki isim</label>
        <input id="holder" className={fieldClass('holder')} autoComplete="cc-name" value={card.holder} onChange={update('holder')} />
        {errors.holder && <span className="field__error">{errors.holder}</span>}
      </div>
      <div className="field">
        <label htmlFor="number">Kart numarası</label>
        <input id="number" className={fieldClass('number')} inputMode="numeric" autoComplete="cc-number"
          placeholder="0000 0000 0000 0000" value={card.number} onChange={update('number')} />
        {errors.number && <span className="field__error">{errors.number}</span>}
        <div className="test-cards">
          {TEST_CARDS.map((test) => (
            <button key={test.number} type="button" onClick={() => setCard((c) => ({ ...c, number: test.number }))}>
              {test.label}
            </button>
          ))}
        </div>
      </div>
      <div className="card-grid">
        <div className="field" style={{ gridColumn: 'span 2' }}>
          <label htmlFor="expiry">Son kullanma</label>
          <input id="expiry" className={fieldClass('expiry')} inputMode="numeric" autoComplete="cc-exp"
            placeholder="AA/YY" value={card.expiry} onChange={update('expiry')} />
          {errors.expiry && <span className="field__error">{errors.expiry}</span>}
        </div>
        <div className="field">
          <label htmlFor="cvc">CVC</label>
          <input id="cvc" className={fieldClass('cvc')} inputMode="numeric" autoComplete="cc-csc"
            placeholder="123" value={card.cvc} onChange={update('cvc')} />
          {errors.cvc && <span className="field__error">{errors.cvc}</span>}
        </div>
      </div>

      {pay.isError && <Alert>{pay.error.message}</Alert>}

      <button className="btn btn--primary btn--block" disabled={pay.isPending}>
        <Lock size={16} /> {pay.isPending ? 'Ödeme alınıyor…' : `${formatTL(checkout.amount)} öde`}
      </button>
      <p className="subtle" style={{ textAlign: 'center' }}>Demo ödeme: gerçek para çekilmez, kart numarası saklanmaz.</p>
    </form>
  )
}

function CurrentSubscription({ subscription, onCancel, cancelling }) {
  const { plan, remaining_credits: credits } = subscription
  const percent = plan.monthly_credits ? Math.round((credits / plan.monthly_credits) * 100) : 100
  const cancelled = subscription.status === 'CANCELLED'

  return (
    <div className="card card--hero stack">
      <div className="row-between wrap">
        <div className="row">
          <Crown size={26} color="var(--yellow-500)" />
          <div>
            <p className="muted">Aktif paketin</p>
            <h2>{plan.name}</h2>
          </div>
        </div>
        {cancelled ? (
          <span className="badge badge--danger">İptal edildi</span>
        ) : (
          <span className="badge badge--yellow">Aktif</span>
        )}
      </div>
      <div className="stack-sm">
        <div className="row-between">
          <strong>{credits == null ? 'Sınırsız kahve' : `${credits} / ${plan.monthly_credits} kahve hakkı`}</strong>
          <span className="muted">
            {cancelled ? 'Bitiş' : 'Yenilenme'}: {formatDate(subscription.expires_at)}
          </span>
        </div>
        <div className="progress"><span style={{ width: `${percent}%` }} /></div>
      </div>
      {subscription.pending_plan && (
        <p className="muted">Gelecek dönem {subscription.pending_plan.name} paketine geçeceksin.</p>
      )}
      {cancelled ? (
        <p className="muted">Hakların dönem sonuna kadar geçerli; sonra paket yenilenmeyecek.</p>
      ) : (
        <div>
          <button type="button" className="btn btn--ghost btn--sm" style={{ color: '#fff', borderColor: 'rgba(255,255,255,.3)' }}
            disabled={cancelling}
            onClick={() => window.confirm('Aboneliği iptal etmek istiyor musun? Hakların dönem sonuna kadar geçerli kalır.') && onCancel()}>
            Aboneliği iptal et
          </button>
        </div>
      )}
    </div>
  )
}

export default function SubscriptionPage() {
  const queryClient = useQueryClient()
  const [checkout, setCheckout] = useState(null)
  const [notice, setNotice] = useState(null)

  const plansQuery = useQuery({ queryKey: queryKeys.plans, queryFn: subscriptionsApi.plans })
  const subscriptionQuery = useSubscription()
  const paymentsQuery = useQuery({ queryKey: queryKeys.payments, queryFn: paymentsApi.history })

  const refresh = (message) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.subscription })
    queryClient.invalidateQueries({ queryKey: queryKeys.payments })
    setCheckout(null)
    setNotice(message)
  }

  const changeWithoutPayment = useMutation({
    mutationFn: subscriptionsApi.changePlan,
    onSuccess: () => refresh('Paket değişikliğin kaydedildi.'),
  })
  const cancel = useMutation({
    mutationFn: subscriptionsApi.cancel,
    onSuccess: () => refresh('Aboneliğin iptal edildi. Hakların dönem sonuna kadar geçerli.'),
  })

  if (plansQuery.isLoading || subscriptionQuery.isLoading) return <Loading />
  if (plansQuery.isError) return <div className="page"><ErrorState error={plansQuery.error} onRetry={plansQuery.refetch} /></div>

  const subscription = subscriptionQuery.data
  const current = subscription?.plan
  const cancelled = subscription?.status === 'CANCELLED'
  const mutationError = changeWithoutPayment.error ?? cancel.error

  function planAction(plan) {
    if (!subscription) {
      return { label: 'Satın al', onClick: () => setCheckout({ plan, mode: 'start', amount: plan.monthly_price_kurus }) }
    }
    if (cancelled) return { label: 'İptal edilen dönem sürüyor', disabled: true }
    if (plan.plan_type === current.plan_type) {
      return subscription.pending_plan
        ? { label: 'Bu pakette kal', onClick: () => changeWithoutPayment.mutate(plan.plan_type) }
        : { label: 'Mevcut paketin', disabled: true }
    }
    if (plan.monthly_price_kurus > current.monthly_price_kurus) {
      const difference = plan.monthly_price_kurus - current.monthly_price_kurus
      return {
        label: `Yükselt · ${formatTL(difference)}`,
        onClick: () => setCheckout({ plan, mode: 'upgrade', amount: difference }),
      }
    }
    if (subscription.pending_plan?.plan_type === plan.plan_type) return { label: 'Gelecek ay geçilecek', disabled: true }
    return {
      label: 'Gelecek ay bu pakete geç',
      ghost: true,
      onClick: () =>
        window.confirm(`${plan.name} paketine geçiş bir sonraki dönem başında uygulanır. Onaylıyor musun?`) &&
        changeWithoutPayment.mutate(plan.plan_type),
    }
  }

  return (
    <div className="page stack" style={{ gap: 28 }}>
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Abonelik</h1>
          <p className="muted">Paketini seç, mobil ödemeyle hemen başla. İstediğin zaman yükselt ya da iptal et.</p>
        </div>
      </div>

      {notice && <Alert variant="success" icon={CheckCircle2}>{notice}</Alert>}
      {mutationError && <Alert>{mutationError.message}</Alert>}

      {subscription && (
        <CurrentSubscription subscription={subscription} onCancel={() => cancel.mutate()} cancelling={cancel.isPending} />
      )}

      {checkout && (
        <PaymentPanel
          checkout={checkout}
          onClose={() => setCheckout(null)}
          onPaid={() => refresh(checkout.mode === 'start' ? 'Ödeme başarılı, paketin aktif! ☕' : 'Paketin yükseltildi, yeni hakların eklendi.')}
        />
      )}

      <section className="plans">
        {plansQuery.data.map((plan) => {
          const action = planAction(plan)
          const featured = plan.plan_type === 'PREMIUM'
          return (
            <div key={plan.plan_type} className={`card plan${featured ? ' plan--featured' : ''}`}>
              {featured && <span className="badge badge--yellow plan__ribbon">En popüler</span>}
              <div className="row-between">
                <h2>{plan.name}</h2>
                {current?.plan_type === plan.plan_type && <span className="badge badge--navy">Senin paketin</span>}
              </div>
              <div className="plan__price">
                {formatTL(plan.monthly_price_kurus)} <small>/ ay</small>
              </div>
              <ul>
                {(PLAN_PERKS[plan.plan_type] ?? []).map((perk) => (
                  <li key={perk}><Check size={18} /> {perk}</li>
                ))}
              </ul>
              <button type="button" className={`btn btn--block ${action.ghost ? 'btn--ghost' : featured ? 'btn--primary' : 'btn--dark'}`}
                disabled={action.disabled || changeWithoutPayment.isPending} onClick={action.onClick}>
                {action.label}
              </button>
            </div>
          )
        })}
      </section>

      <section className="stack-sm">
        <h2>Ödeme geçmişi</h2>
        {paymentsQuery.data?.items.length === 0 && <p className="muted">Henüz ödeme yok.</p>}
        {paymentsQuery.data?.items.map((payment) => (
          <div key={payment.transaction_id} className="card row-between wrap" style={{ padding: 14 }}>
            <div className="row">
              <CreditCard size={20} color="var(--text-muted)" />
              <div>
                <strong>{formatTL(payment.amount_kurus)}</strong>
                <p className="subtle">•••• {payment.card_last4} · {formatDateTime(payment.created_at)}</p>
              </div>
            </div>
            <span className={`badge ${payment.status === 'SUCCESS' ? 'badge--open' : 'badge--danger'}`}>
              {payment.status === 'SUCCESS' ? 'Başarılı' : 'Reddedildi'}
            </span>
          </div>
        ))}
      </section>
    </div>
  )
}
