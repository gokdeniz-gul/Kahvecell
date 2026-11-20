import { useEffect, useRef } from 'react'

import { BASE_URL } from '../api/client'
import { useAuthStore } from '../store/authStore'

const EVENT_TYPES = ['order.created', 'order.updated']

/**
 * Sunucudan canlı olay dinler (Server-Sent Events).
 * Sunucu "sipariş durumu değişti" dediği anda `onEvent` çağrılır; sayfanın tekrar tekrar
 * sormasına (polling) gerek kalmaz.
 *
 * Tarayıcının EventSource'u başlık gönderemediği için token adreste gider. Token yenilenince
 * (store değişince) bağlantı yeni token'la kendiliğinden yeniden kurulur.
 */
export function useEventStream(path, onEvent, { enabled = true } = {}) {
  const token = useAuthStore((state) => state.accessToken)
  const handlerRef = useRef(onEvent)

  useEffect(() => {
    handlerRef.current = onEvent
  })

  useEffect(() => {
    if (!enabled || !token || !path || typeof EventSource === 'undefined') return undefined

    const source = new EventSource(`${BASE_URL}${path}?token=${encodeURIComponent(token)}`)
    const handle = (message) => {
      try {
        handlerRef.current?.(JSON.parse(message.data))
      } catch {
        // bozuk mesajı yok say
      }
    }
    EVENT_TYPES.forEach((type) => source.addEventListener(type, handle))
    return () => source.close()
  }, [path, token, enabled])
}
