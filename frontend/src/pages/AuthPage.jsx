import { ArrowLeft, BadgeCheck, MapPin, QrCode, Smartphone, Zap } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { authApi } from '../api/endpoints'
import Logo from '../components/Logo'
import { Alert } from '../components/StateViews'
import { normalizePhone } from '../lib/format'
import { useAuthStore } from '../store/authStore'

/**
 * Case 7.1 akışı: GSM gir → SMS kodu (simülasyon 1234) → ilk girişte profil tamamla → ana sayfa.
 * Giriş ve kayıt aynı bileşeni kullanır; sadece ilk adımda çağrılan endpoint farklıdır.
 */
export default function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const navigate = useNavigate()
  const location = useLocation()
  const setSession = useAuthStore((state) => state.setSession)
  const setUser = useAuthStore((state) => state.setUser)

  const [step, setStep] = useState('phone') // phone → code → profile
  const [phoneInput, setPhoneInput] = useState('')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [profile, setProfile] = useState({ full_name: '', email: '' })
  const [fieldError, setFieldError] = useState('')
  const [apiError, setApiError] = useState(null)
  const [busy, setBusy] = useState(false)

  const goHome = () => navigate(location.state?.from ?? '/', { replace: true })

  async function run(action) {
    setApiError(null)
    setBusy(true)
    try {
      await action()
    } catch (error) {
      setApiError(error)
    } finally {
      setBusy(false)
    }
  }

  function submitPhone(event) {
    event.preventDefault()
    const normalized = normalizePhone(phoneInput)
    if (!normalized) return setFieldError('5 ile başlayan 10 haneli GSM numaranı gir (örn. 532 123 45 67).')
    setFieldError('')
    run(async () => {
      await (isRegister ? authApi.register(normalized) : authApi.login(normalized))
      setPhone(normalized)
      setCode('')
      setStep('code')
    })
  }

  function submitCode(event) {
    event.preventDefault()
    if (!/^\d{4}$/.test(code)) return setFieldError('Kod 4 haneli olmalı.')
    setFieldError('')
    run(async () => {
      const result = await authApi.verifyOtp(phone, code)
      setSession({ accessToken: result.access_token, refreshToken: result.refresh_token, user: result.user })
      if (result.is_profile_complete) goHome()
      else setStep('profile')
    })
  }

  function submitProfile(event) {
    event.preventDefault()
    const fullName = profile.full_name.trim()
    const email = profile.email.trim()
    if (fullName.length < 2) return setFieldError('Adını ve soyadını gir.')
    if (email && !/^\S+@\S+\.\S+$/.test(email)) return setFieldError('Geçerli bir e-posta gir.')
    setFieldError('')
    run(async () => {
      const user = await authApi.updateMe({ full_name: fullName, ...(email && { email }) })
      setUser(user)
      goHome()
    })
  }

  const stepIndex = { phone: 0, code: 1, profile: 2 }[step]
  const errorBox = (fieldError || apiError) && <Alert>{fieldError || apiError.message}</Alert>

  return (
    <div className="auth">
      <aside className="auth__brand">
        <Logo to={isRegister ? '/kayit' : '/giris'} />
        <div className="auth__headline">
          <h1>
            Kahven hazır,
            <br />
            <span>sıra beklemeden.</span>
          </h1>
          <p>Aylık paketinle anlaşmalı dükkânlardan sipariş ver, QR kodunla kasada saniyeler içinde teslim al.</p>
        </div>
        <div className="auth__perks">
          <ul>
            <li><MapPin size={18} /> Yakınındaki dükkânları haritada gör</li>
            <li><Zap size={18} /> Mobil ödemeyle tek dokunuşta abone ol</li>
            <li><QrCode size={18} /> QR ile hızlı ve güvenli teslim</li>
          </ul>
        </div>
      </aside>

      <section className="auth__panel">
        <div className="auth__form stack">
          <div className="steps" aria-hidden>
            {[0, 1, 2].map((i) => (
              <span key={i} className={i <= stepIndex ? 'done' : ''} />
            ))}
          </div>

          {step === 'phone' && (
            <form className="stack" onSubmit={submitPhone} noValidate>
              <div className="stack-sm">
                <h2>{isRegister ? 'Hesap oluştur' : 'Tekrar hoş geldin'}</h2>
                <p className="muted">
                  {isRegister ? 'GSM numaranla saniyeler içinde kayıt ol.' : 'GSM numaranı gir, sana bir doğrulama kodu gönderelim.'}
                </p>
              </div>
              <div className="field">
                <label htmlFor="phone">GSM numarası</label>
                <div className="input-group">
                  <span className="input-group__prefix">+90</span>
                  <input
                    id="phone"
                    className={`input${fieldError ? ' input--invalid' : ''}`}
                    inputMode="tel"
                    autoComplete="tel-national"
                    placeholder="532 123 45 67"
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    autoFocus
                  />
                </div>
              </div>
              {errorBox}
              <button className="btn btn--primary btn--block" disabled={busy}>
                <Smartphone size={18} /> {busy ? 'Gönderiliyor…' : 'Doğrulama kodu gönder'}
              </button>
              <p className="auth__switch">
                {isRegister ? (
                  <>Zaten hesabın var mı? <Link to="/giris">Giriş yap</Link></>
                ) : (
                  <>Hesabın yok mu? <Link to="/kayit">Kayıt ol</Link></>
                )}
              </p>
            </form>
          )}

          {step === 'code' && (
            <form className="stack" onSubmit={submitCode} noValidate>
              <button type="button" className="back-link" onClick={() => setStep('phone')} style={{ border: 0, background: 'none', padding: 0, cursor: 'pointer' }}>
                <ArrowLeft size={16} /> Numarayı değiştir
              </button>
              <div className="stack-sm">
                <h2>Kodu gir</h2>
                <p className="muted">+90 {phone} numarasına gönderilen 4 haneli kodu yaz.</p>
              </div>
              <input
                className={`input input--otp${fieldError ? ' input--invalid' : ''}`}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={4}
                placeholder="••••"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                aria-label="Doğrulama kodu"
                autoFocus
              />
              <Alert variant="info" icon={BadgeCheck}>
                Demo ortamı: gerçek SMS gönderilmez, kod her zaman <strong>1234</strong>.
              </Alert>
              {errorBox}
              <button className="btn btn--primary btn--block" disabled={busy}>
                {busy ? 'Doğrulanıyor…' : 'Doğrula ve devam et'}
              </button>
            </form>
          )}

          {step === 'profile' && (
            <form className="stack" onSubmit={submitProfile} noValidate>
              <div className="stack-sm">
                <h2>Seni tanıyalım</h2>
                <p className="muted">Siparişlerinde adın görünecek. E-posta isteğe bağlı; kahve tercihlerini ve alerjenlerini daha sonra Profil sayfasından ekleyebilirsin.</p>
              </div>
              <div className="field">
                <label htmlFor="full_name">Ad soyad</label>
                <input
                  id="full_name"
                  className="input"
                  autoComplete="name"
                  value={profile.full_name}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  autoFocus
                />
              </div>
              <div className="field">
                <label htmlFor="email">E-posta</label>
                <input
                  id="email"
                  type="email"
                  className="input"
                  autoComplete="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                />
              </div>
              {errorBox}
              <button className="btn btn--primary btn--block" disabled={busy}>
                {busy ? 'Kaydediliyor…' : 'Başlayalım'}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  )
}
