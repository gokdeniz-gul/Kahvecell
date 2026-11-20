import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, CreditCard, Lock, ShieldCheck, X, XCircle } from 'lucide-react'
import { useState } from 'react'

import { paymentsApi, subscriptionsApi } from '../api/endpoints'
import { formatTL } from '../lib/format'
import { formatCardNumber, formatExpiry, validateCard } from '../lib/validation'
import { Alert } from './StateViews'

const TEST_CARDS = [
  { number: '4242 4242 4242 4242', label: '4242… başarılı' },
  { number: '4000 0000 0000 0002', label: '4000…0002 reddedilir' },
]
const STEPS = ['Kart bilgileri', 'Onay', 'Sonuç']

function Steps({ current }) {
  return (
    <ol className="pay-steps" aria-label="Ödeme adımları">
      {STEPS.map((label, index) => (
        <li key={label} className={index <= current ? 'done' : ''} aria-current={index === current ? 'step' : undefined}>
          <span>{index + 1}</span> {label}
        </li>
      ))}
    </ol>
  )
}

/**
 * Case 12.2 ödeme akışı: 1) kart formu → 2) onay ekranı → 3) sonuç (başarılı / reddedildi).
 * Ödeme başarılıysa transaction_id ile abonelik başlatılır ya da yükseltilir.
 */
export default function PaymentFlow({ checkout, onPaid, onClose }) {
  const [step, setStep] = useState('form') // form → confirm → result
  const [card, setCard] = useState({ holder: '', number: '', expiry: '', cvc: '' })
  const [errors, setErrors] = useState({})
  const [result, setResult] = useState(null) // { ok, transactionId, message }

  const update = (field) => (event) => {
    let value = event.target.value
    if (field === 'number') value = formatCardNumber(value)
    if (field === 'expiry') value = formatExpiry(value)
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
      await (checkout.mode === 'start'
        ? subscriptionsApi.start(checkout.plan.plan_type, payment.transaction_id)
        : subscriptionsApi.changePlan(checkout.plan.plan_type, payment.transaction_id))
      return payment
    },
    onSuccess: (payment) => {
      setResult({ ok: true, transactionId: payment.transaction_id })
      setStep('result')
      onPaid?.()
    },
    onError: (error) => {
      if (error.code === 'PAYMENT_DECLINED') {
        setResult({ ok: false, transactionId: error.details?.transaction_id, message: error.message })
        setStep('result')
        onPaid?.() // reddedilen deneme de ödeme geçmişine yazıldı
      }
    },
  })

  function goToConfirm(event) {
    event.preventDefault()
    const found = validateCard(card)
    setErrors(found)
    if (Object.keys(found).length === 0) setStep('confirm')
  }

  function retryWithAnotherCard() {
    pay.reset()
    setResult(null)
    setCard((current) => ({ ...current, number: '', cvc: '' }))
    setStep('form')
  }

  const title = checkout.mode === 'start' ? `${checkout.plan.name} paketini al` : `${checkout.plan.name} paketine yükselt`
  const fieldClass = (name) => `input${errors[name] ? ' input--invalid' : ''}`
  const last4 = card.number.replace(/\s/g, '').slice(-4)

  return (
    <section className="card pay-panel stack" aria-labelledby="pay-title">
      <div className="row-between">
        <h2 id="pay-title">{title}</h2>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Kapat"><X size={20} /></button>
      </div>
      <Steps current={{ form: 0, confirm: 1, result: 2 }[step]} />

      {step === 'form' && (
        <form className="stack" onSubmit={goToConfirm} noValidate>
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
          <button className="btn btn--dark btn--block">Devam et</button>
        </form>
      )}

      {step === 'confirm' && (
        <div className="stack">
          <p className="muted">Lütfen bilgileri kontrol et. Onayladığında kartından çekim yapılacak.</p>
          <div className="pay-summary">
            <div className="summary-line"><span className="muted">Paket</span><strong>{checkout.plan.name}</strong></div>
            <div className="summary-line">
              <span className="muted">İşlem</span>
              <span>{checkout.mode === 'start' ? 'Yeni abonelik (aylık)' : 'Paket yükseltme (fiyat farkı)'}</span>
            </div>
            <div className="summary-line"><span className="muted">Kart</span><span><CreditCard size={15} /> •••• {last4} · {card.holder}</span></div>
            <div className="summary-line pay-summary__total"><span>Ödenecek tutar</span><strong>{formatTL(checkout.amount)}</strong></div>
          </div>
          {pay.isError && pay.error.code !== 'PAYMENT_DECLINED' && <Alert>{pay.error.message}</Alert>}
          <div className="row">
            <button type="button" className="btn btn--ghost" disabled={pay.isPending} onClick={() => setStep('form')}>
              <ArrowLeft size={16} /> Geri
            </button>
            <button type="button" className="btn btn--primary" style={{ flex: 1 }} disabled={pay.isPending} onClick={() => pay.mutate()}>
              <Lock size={16} /> {pay.isPending ? 'Ödeme alınıyor…' : `Onayla ve ${formatTL(checkout.amount)} öde`}
            </button>
          </div>
          <p className="subtle" style={{ textAlign: 'center' }}>
            <ShieldCheck size={14} style={{ verticalAlign: '-2px' }} /> Demo ödeme: gerçek para çekilmez, kart numarası saklanmaz.
          </p>
        </div>
      )}

      {step === 'result' && result && (
        <div className="pay-result" role="status" aria-live="polite">
          {result.ok ? (
            <>
              <CheckCircle2 size={56} className="pay-result__icon pay-result__icon--ok" />
              <h3>Ödeme başarılı</h3>
              <p className="muted">
                {checkout.mode === 'start' ? `${checkout.plan.name} paketin aktif. Afiyet olsun! ☕` : `${checkout.plan.name} paketine geçtin, yeni hakların eklendi.`}
              </p>
            </>
          ) : (
            <>
              <XCircle size={56} className="pay-result__icon pay-result__icon--fail" />
              <h3>Ödeme reddedildi</h3>
              <p className="muted">{result.message}</p>
            </>
          )}
          <div className="pay-summary" style={{ width: '100%' }}>
            <div className="summary-line"><span className="muted">Tutar</span><span>{formatTL(checkout.amount)}</span></div>
            {result.transactionId && (
              <div className="summary-line"><span className="muted">İşlem numarası</span><code>{result.transactionId}</code></div>
            )}
          </div>
          {result.ok ? (
            <button type="button" className="btn btn--primary btn--block" onClick={onClose}>Tamam</button>
          ) : (
            <div className="row" style={{ width: '100%' }}>
              <button type="button" className="btn btn--ghost" onClick={onClose}>Vazgeç</button>
              <button type="button" className="btn btn--dark" style={{ flex: 1 }} onClick={retryWithAnotherCard}>Başka kartla dene</button>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
