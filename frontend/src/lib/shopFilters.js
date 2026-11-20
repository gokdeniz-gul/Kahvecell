/** Dükkân filtre seçenekleri ve sorgu parametresine çeviri. */

export const DEFAULT_FILTERS = { openNow: false, radiusKm: '', minRating: '', sort: 'distance' }

export const RADIUS_OPTIONS = [
  { value: '', label: 'Tüm mesafeler' },
  { value: '1', label: '1 km içinde' },
  { value: '3', label: '3 km içinde' },
  { value: '5', label: '5 km içinde' },
]
export const RATING_OPTIONS = [
  { value: '', label: 'Tüm puanlar' },
  { value: '4', label: '4.0 ve üzeri' },
  { value: '4.5', label: '4.5 ve üzeri' },
]
export const SORT_OPTIONS = [
  { value: 'distance', label: 'En yakın' },
  { value: 'rating', label: 'En yüksek puan' },
  { value: 'name', label: 'İsme göre' },
]

/** Filtreleri backend'in beklediği sorgu parametrelerine çevirir (boş olanları göndermez). */
export function filtersToParams(filters) {
  return {
    ...(filters.openNow && { open_now: true }),
    ...(filters.radiusKm && { radius_km: Number(filters.radiusKm) }),
    ...(filters.minRating && { min_rating: Number(filters.minRating) }),
    sort: filters.sort,
  }
}
