import { useEffect, useState } from 'react'

/** Konum izni yoksa haritayı Taksim'e göre gösteriyoruz. */
export const FALLBACK_LOCATION = { lat: 41.037, lng: 28.985, label: 'Taksim' }

const hasGeolocation = typeof navigator !== 'undefined' && 'geolocation' in navigator

/**
 * Tarayıcıdan kullanıcının konumunu ister.
 * Dönen değer: { position: {lat, lng}, status: 'loading' | 'granted' | 'fallback' }
 */
export function useUserLocation() {
  const [state, setState] = useState(() =>
    hasGeolocation
      ? { position: FALLBACK_LOCATION, status: 'loading' }
      : { position: FALLBACK_LOCATION, status: 'fallback' },
  )

  useEffect(() => {
    if (!hasGeolocation) return
    navigator.geolocation.getCurrentPosition(
      ({ coords }) =>
        setState({
          position: { lat: Number(coords.latitude.toFixed(5)), lng: Number(coords.longitude.toFixed(5)) },
          status: 'granted',
        }),
      () => setState({ position: FALLBACK_LOCATION, status: 'fallback' }),
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 5 * 60 * 1000 },
    )
  }, [])

  return state
}
