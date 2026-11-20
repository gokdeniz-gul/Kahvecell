import { useMutation } from '@tanstack/react-query'
import { CheckCircle2, ShieldAlert, UserRound } from 'lucide-react'
import { useState } from 'react'

import { authApi } from '../api/endpoints'
import { Alert } from '../components/StateViews'
import { ALLERGENS, COFFEE_TYPES } from '../lib/format'
import { useAuthStore } from '../store/authStore'

/** Çoklu seçim düğmeleri (aria-pressed ile ekran okuyucuya seçili olduğu bildirilir). */
function ChipGroup({ label, options, selected, onToggle }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option.value} type="button" aria-pressed={selected.includes(option.value)}
          onClick={() => onToggle(option.value)}>
          {option.label}
        </button>
      ))}
    </div>
  )
}

const toggle = (list, value) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value])

/** Case 3.1: profil — ad soyad, e-posta, tercih edilen kahve türleri, alerjenler. */
export default function ProfilePage() {
  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)
  const [form, setForm] = useState(() => ({
    full_name: user?.full_name ?? '',
    email: user?.email ?? '',
    coffee_types: user?.preferences?.coffee_types ?? [],
    allergens: user?.preferences?.allergens ?? [],
  }))
  const [fieldError, setFieldError] = useState('')

  const save = useMutation({
    mutationFn: () =>
      authApi.updateMe({
        full_name: form.full_name.trim(),
        email: form.email.trim() || null,
        preferences: { coffee_types: form.coffee_types, allergens: form.allergens },
      }),
    onSuccess: setUser,
  })

  function submit(event) {
    event.preventDefault()
    if (form.full_name.trim().length < 2) return setFieldError('Adını ve soyadını gir.')
    if (form.email.trim() && !/^\S+@\S+\.\S+$/.test(form.email.trim())) return setFieldError('Geçerli bir e-posta gir.')
    setFieldError('')
    save.mutate()
  }

  const set = (field) => (value) => {
    save.reset()
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Profilim</h1>
          <p className="muted">Tercihlerine göre sana uygun kahveleri öne çıkarır, alerjenlerin için sipariş ekranında uyarırız.</p>
        </div>
      </div>

      <form className="card stack profile-form" onSubmit={submit} noValidate style={{ gap: 24 }}>
        <div className="row">
          <span className="stat-card__icon"><UserRound size={22} /></span>
          <div>
            <strong>+90 {user?.phone_number}</strong>
            <p className="subtle">Telefon numarası giriş için kullanılır ve değiştirilemez.</p>
          </div>
        </div>

        <div className="field">
          <label htmlFor="full_name">Ad soyad</label>
          <input id="full_name" className="input" autoComplete="name" value={form.full_name}
            onChange={(e) => set('full_name')(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="email">E-posta <span className="subtle">(isteğe bağlı)</span></label>
          <input id="email" type="email" className="input" autoComplete="email" value={form.email}
            onChange={(e) => set('email')(e.target.value)} />
        </div>

        <div className="field">
          <label>Sevdiğin kahveler</label>
          <ChipGroup label="Sevdiğin kahveler" options={COFFEE_TYPES} selected={form.coffee_types}
            onToggle={(value) => set('coffee_types')(toggle(form.coffee_types, value))} />
        </div>

        <div className="field">
          <label><ShieldAlert size={16} style={{ verticalAlign: '-3px' }} /> Alerjenlerin</label>
          <ChipGroup label="Alerjenlerin" options={ALLERGENS} selected={form.allergens}
            onToggle={(value) => set('allergens')(toggle(form.allergens, value))} />
          <span className="field__hint">Sipariş verirken seçtiğin süt bu alerjenlerden birini içeriyorsa uyarı görürsün.</span>
        </div>

        {fieldError && <Alert>{fieldError}</Alert>}
        {save.isError && <Alert>{save.error.message}</Alert>}
        {save.isSuccess && <Alert variant="success" icon={CheckCircle2}>Profilin kaydedildi.</Alert>}

        <button className="btn btn--primary" disabled={save.isPending} style={{ alignSelf: 'flex-start' }}>
          {save.isPending ? 'Kaydediliyor…' : 'Kaydet'}
        </button>
      </form>
    </div>
  )
}
