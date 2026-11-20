import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, CheckCircle2, CreditCard, Crown } from 'lucide-react'
import { useState } from 'react'

import { paymentsApi, queryKeys, subscriptionsApi } from '../api/endpoints'
import PaymentFlow from '../components/PaymentFlow'
import { Alert, ErrorState, Loading } from '../components/StateViews'
import { useSubscription } from '../hooks/useSubscription'
import { formatDate, formatDateTime, formatTL } from '../lib/format'

const PLAN_PERKS = {
  STARTER: ['Ayda 10 kahve', 'Tüm anlaşmalı dükkânlar'],
  PREMIUM: ['Ayda 20 kahve', 'Tüm anlaşmalı dükkânlar', '2 misafir hakkı'],
  UNLIMITED: ['Sınırsız kahve', 'Tüm anlaşmalı dükkânlar', '5 misafir hakkı', 'Öncelikli hazırlanma'],
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

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.subscription })
    queryClient.invalidateQueries({ queryKey: queryKeys.payments })
  }
  const refresh = (message) => {
    invalidate()
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
        <PaymentFlow
          checkout={checkout}
          onPaid={invalidate}
          onClose={() => setCheckout(null)}
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
