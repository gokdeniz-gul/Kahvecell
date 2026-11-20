import L from 'leaflet'
import { useEffect } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { Link } from 'react-router-dom'

import { formatDistance } from '../lib/format'

// Ücretsiz ve API anahtarı gerektirmeyen OpenStreetMap görüntüsü.
// Renkleri CSS ile (.map-tiles) yumuşatıyoruz ki markanın lacivert-sarı işaretleri öne çıksın.
// Not: OSM sunucuları gönüllülerce işletilir; düşük trafikli projeler için uygundur.
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıcıları'

// Leaflet'in varsayılan ikonları Vite ile düzgün yüklenmiyor; kendi işaretlerimizi HTML ile çiziyoruz.
const CUP_SVG =
  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v2M14 2v2M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1M6 2v2"/></svg>'

const shopIcon = (active) =>
  L.divIcon({
    className: '',
    html: `<div class="map-pin${active ? ' map-pin--active' : ''}">${CUP_SVG}</div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 38],
    popupAnchor: [0, -36],
  })

const meIcon = L.divIcon({ className: '', html: '<div class="map-me"></div>', iconSize: [18, 18], iconAnchor: [9, 9] })

/** Harita açılınca tüm dükkânlar (ve kullanıcı) ekrana sığsın. */
function FitBounds({ points }) {
  const map = useMap()
  const key = points.map((p) => p.join(',')).join('|')
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 15)
    else if (points.length > 1) map.fitBounds(points, { padding: [48, 48], maxZoom: 15 })
    // Sadece noktalar değişince çalışsın.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, key])
  return null
}

export default function ShopMap({ shops, userPosition, activeShopId, onSelect, interactive = true }) {
  const points = shops.map((shop) => [shop.latitude, shop.longitude])
  if (userPosition) points.push([userPosition.lat, userPosition.lng])
  const center = points[0] ?? [41.037, 28.985]

  return (
    <MapContainer
      center={center}
      zoom={13}
      scrollWheelZoom={interactive}
      dragging={interactive}
      zoomControl={interactive}
      style={{ height: '100%', width: '100%', minHeight: 'inherit' }}
    >
      <TileLayer url={TILE_URL} attribution={ATTRIBUTION} maxZoom={19} className="map-tiles" />
      <FitBounds points={points} />

      {userPosition && <Marker position={[userPosition.lat, userPosition.lng]} icon={meIcon} />}

      {shops.map((shop) => (
        <Marker
          key={shop.id}
          position={[shop.latitude, shop.longitude]}
          icon={shopIcon(shop.id === activeShopId)}
          eventHandlers={{ click: () => onSelect?.(shop.id) }}
        >
          {interactive && (
            <Popup>
              <div className="map-popup">
                <strong>{shop.name}</strong>
                <div className="muted">
                  ★ {shop.rating.toFixed(1)}
                  {shop.distance_km != null && ` · ${formatDistance(shop.distance_km)}`}
                </div>
                <Link to={`/dukkan/${shop.id}`}>Menüyü gör →</Link>
              </div>
            </Popup>
          )}
        </Marker>
      ))}
    </MapContainer>
  )
}
