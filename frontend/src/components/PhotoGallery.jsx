import { Coffee } from 'lucide-react'
import { useState } from 'react'

/** Dükkân fotoğraf galerisi: büyük görsel + küçük resimlerle seçim (case 3.3). */
export default function PhotoGallery({ photos, shopName }) {
  const [active, setActive] = useState(0)

  if (!photos?.length) {
    return (
      <div className="gallery gallery--empty" aria-label={`${shopName} için fotoğraf yok`}>
        <Coffee size={48} />
      </div>
    )
  }

  const current = photos[Math.min(active, photos.length - 1)]
  return (
    <div className="gallery">
      <img className="gallery__main" src={current.url} alt={current.alt_text} />
      {photos.length > 1 && (
        <div className="gallery__thumbs" role="group" aria-label="Fotoğraflar">
          {photos.map((photo, index) => (
            <button
              key={photo.url}
              type="button"
              className="gallery__thumb"
              aria-pressed={index === active}
              aria-label={`Fotoğraf ${index + 1}: ${photo.alt_text}`}
              onClick={() => setActive(index)}
            >
              <img src={photo.url} alt="" loading="lazy" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
