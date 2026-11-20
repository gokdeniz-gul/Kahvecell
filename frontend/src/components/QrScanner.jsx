import jsQR from 'jsqr'
import { Camera, ClipboardPaste, ImageUp, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Alert } from './StateViews'

const MODES = [
  { id: 'camera', label: 'Kamera', icon: Camera },
  { id: 'image', label: 'Resim yükle', icon: ImageUp },
  { id: 'paste', label: 'Metin yapıştır', icon: ClipboardPaste },
]

/** Görüntüdeki QR kodu çöz; bulunamazsa null. */
function decodeFrom(source, width, height) {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d', { willReadFrequently: true })
  context.drawImage(source, 0, 0, width, height)
  const { data } = context.getImageData(0, 0, width, height)
  return jsQR(data, width, height)?.data ?? null
}

function CameraReader({ onResult }) {
  const videoRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let stream
    let frame
    let stopped = false

    const scan = () => {
      const video = videoRef.current
      if (stopped || !video) return
      if (video.readyState === video.HAVE_ENOUGH_DATA) {
        const text = decodeFrom(video, video.videoWidth, video.videoHeight)
        if (text) return onResult(text)
      }
      frame = requestAnimationFrame(scan)
    }

    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: 'environment' } })
      .then((media) => {
        stream = media
        if (stopped) return media.getTracks().forEach((track) => track.stop())
        videoRef.current.srcObject = media
        videoRef.current.play()
        frame = requestAnimationFrame(scan)
      })
      .catch(() => setError('Kameraya erişilemedi. İzin verin ya da "Resim yükle" / "Metin yapıştır"ı kullanın.'))

    if (!navigator.mediaDevices) {
      queueMicrotask(() => setError('Bu tarayıcı kamerayı desteklemiyor.'))
    }

    return () => {
      stopped = true
      cancelAnimationFrame(frame)
      stream?.getTracks().forEach((track) => track.stop())
    }
  }, [onResult])

  return (
    <div className="stack-sm">
      <div className="scanner-video">
        <video ref={videoRef} muted playsInline aria-label="Kamera görüntüsü" />
        <span className="scanner-video__frame" aria-hidden />
      </div>
      {error ? <Alert>{error}</Alert> : <p className="subtle">QR kodu çerçevenin içine getirin.</p>}
    </div>
  )
}

function ImageReader({ onResult }) {
  const [error, setError] = useState(null)

  async function handleFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setError(null)
    try {
      const bitmap = await createImageBitmap(file)
      const text = decodeFrom(bitmap, bitmap.width, bitmap.height)
      if (text) onResult(text)
      else setError('Resimde QR kod bulunamadı.')
    } catch {
      setError('Resim okunamadı.')
    }
  }

  return (
    <div className="field">
      <label htmlFor="qr-image">Müşterinin QR ekran görüntüsü</label>
      <input id="qr-image" className="input" type="file" accept="image/*" onChange={handleFile} />
      {error && <span className="field__error">{error}</span>}
    </div>
  )
}

function PasteReader({ onResult }) {
  const [text, setText] = useState('')
  return (
    <form
      className="stack-sm"
      onSubmit={(event) => {
        event.preventDefault()
        if (text.trim()) onResult(text.trim())
      }}
    >
      <div className="field">
        <label htmlFor="qr-text">QR içeriği</label>
        <textarea id="qr-text" className="input" rows={4} placeholder='{"order_id": "...", "signature": "..."}'
          value={text} onChange={(e) => setText(e.target.value)} />
      </div>
      <button className="btn btn--dark" disabled={!text.trim()}>Doğrula</button>
    </form>
  )
}

/** Dükkânda müşterinin QR'ını okutma penceresi. Okunan metin `onResult` ile verilir. */
export default function QrScanner({ title = 'QR kodu okut', onResult, onClose, children }) {
  const [mode, setMode] = useState('camera')
  const dialogRef = useRef(null)

  useEffect(() => {
    dialogRef.current?.focus()
    const onKey = (event) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="modal card stack"
        role="dialog"
        aria-modal="true"
        aria-labelledby="qr-scanner-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="row-between">
          <h2 id="qr-scanner-title">{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Kapat"><X size={20} /></button>
        </div>

        <div className="segmented" role="tablist" aria-label="Okutma yöntemi">
          {MODES.map(({ id, label, icon: Icon }) => (
            <button key={id} type="button" role="tab" aria-selected={mode === id} aria-pressed={mode === id}
              onClick={() => setMode(id)}>
              <Icon size={16} style={{ verticalAlign: '-3px', marginRight: 6 }} />{label}
            </button>
          ))}
        </div>

        {mode === 'camera' && <CameraReader onResult={onResult} />}
        {mode === 'image' && <ImageReader onResult={onResult} />}
        {mode === 'paste' && <PasteReader onResult={onResult} />}

        {children}
      </div>
    </div>
  )
}
