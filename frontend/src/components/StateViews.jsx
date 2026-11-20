import { AlertTriangle, Inbox } from 'lucide-react'

/** Case 4.3: her ekranda yükleniyor / hata / boş durumları. */

export function Loading({ label = 'Yükleniyor…' }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <div className="spinner" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state" role="alert">
      <div className="state__icon" style={{ color: 'var(--danger)' }}>
        <AlertTriangle size={28} />
      </div>
      <h3>Bir şeyler ters gitti</h3>
      <p>{error?.message ?? 'Beklenmeyen bir hata oluştu.'}</p>
      {onRetry && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>
          Tekrar dene
        </button>
      )}
    </div>
  )
}

export function EmptyState({ icon: Icon = Inbox, title, children, action }) {
  return (
    <div className="state">
      <div className="state__icon">
        <Icon size={28} />
      </div>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

export function Alert({ variant = 'error', icon: Icon = AlertTriangle, children }) {
  return (
    <div className={`alert alert--${variant}`} role={variant === 'error' ? 'alert' : 'status'}>
      <Icon size={18} />
      <div>{children}</div>
    </div>
  )
}
