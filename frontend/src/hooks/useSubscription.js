import { useQuery } from '@tanstack/react-query'

import { queryKeys, subscriptionsApi } from '../api/endpoints'

/** Aktif abonelik (yoksa data: null). Birçok sayfa kullandığı için ortak hook. */
export function useSubscription() {
  return useQuery({ queryKey: queryKeys.subscription, queryFn: subscriptionsApi.mine })
}
