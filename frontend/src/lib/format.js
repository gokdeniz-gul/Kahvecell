const tl = new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' })
const dateTime = new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short' })
const clock = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' })
const dateOnly = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })

export const formatTL = (kurus) => tl.format(kurus / 100)
export const formatDateTime = (iso) => dateTime.format(new Date(iso))
export const formatClock = (iso) => clock.format(new Date(iso))
export const formatDate = (iso) => dateOnly.format(new Date(iso))
export const formatTime = (hhmmss) => hhmmss.slice(0, 5)
export const formatDistance = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`)

export const ORDER_STATUS = {
  PENDING: { label: 'Sipariş alındı', hint: 'Dükkân siparişini onaylayacak.' },
  ACCEPTED: { label: 'Kabul edildi', hint: 'Barista siparişini sıraya aldı.' },
  PREPARING: { label: 'Hazırlanıyor', hint: 'Kahven hazırlanıyor.' },
  READY: { label: 'Hazır', hint: 'Kasada QR kodunu okut, kahveni al.' },
  COMPLETED: { label: 'Teslim edildi', hint: 'Afiyet olsun!' },
  CANCELLED: { label: 'İptal edildi', hint: 'Kahve hakkın iade edildi.' },
}

export const ORDER_FLOW = ['PENDING', 'ACCEPTED', 'PREPARING', 'READY', 'COMPLETED']
export const ACTIVE_ORDER = ['PENDING', 'ACCEPTED', 'PREPARING', 'READY']

/** Dükkân panelinde her durumun "sonraki adım" düğmesi. Teslim (COMPLETED) QR okutmayı gerektirir. */
export const NEXT_ACTION = {
  PENDING: { status: 'ACCEPTED', label: 'Kabul et' },
  ACCEPTED: { status: 'PREPARING', label: 'Hazırlamaya başla' },
  PREPARING: { status: 'READY', label: 'Hazır' },
  READY: { status: 'COMPLETED', label: 'QR okut ve teslim et', needsQr: true },
}

export const STAFF_ROLES = ['SHOP_OWNER', 'ADMIN']

export const SIZES = [
  { value: 'S', label: 'Küçük' },
  { value: 'M', label: 'Orta' },
  { value: 'L', label: 'Büyük' },
]
export const SUGARS = [
  { value: 'NONE', label: 'Şekersiz' },
  { value: 'LESS', label: 'Az' },
  { value: 'NORMAL', label: 'Orta' },
  { value: 'EXTRA', label: 'Bol' },
]
export const MILKS = [
  { value: 'NONE', label: 'Sütsüz' },
  { value: 'WHOLE', label: 'Tam yağlı' },
  { value: 'LACTOSE_FREE', label: 'Laktozsuz' },
  { value: 'OAT', label: 'Yulaf' },
  { value: 'ALMOND', label: 'Badem' },
]
export const COFFEE_TYPES = [
  { value: 'ESPRESSO', label: 'Espresso' },
  { value: 'LATTE', label: 'Latte' },
  { value: 'CAPPUCCINO', label: 'Cappuccino' },
  { value: 'FILTER', label: 'Filtre kahve' },
  { value: 'TURKISH', label: 'Türk kahvesi' },
  { value: 'COLD_BREW', label: 'Soğuk kahve' },
  { value: 'TEA', label: 'Çay' },
]

export const ALLERGENS = [
  { value: 'LACTOSE', label: 'Laktoz' },
  { value: 'GLUTEN', label: 'Gluten' },
  { value: 'TREE_NUTS', label: 'Kabuklu yemiş (badem, fındık)' },
  { value: 'SOY', label: 'Soya' },
]

/** Hangi süt seçimi hangi alerjeni içerir? (Yulaf çapraz bulaşma nedeniyle gluten içerebilir.) */
const MILK_ALLERGENS = { WHOLE: ['LACTOSE'], ALMOND: ['TREE_NUTS'], OAT: ['GLUTEN'] }

/** Kullanıcının alerjenleriyle çakışan süt seçimi için uyarı listesi döner. */
export function allergenConflicts(milk, userAllergens = []) {
  return (MILK_ALLERGENS[milk] ?? []).filter((allergen) => userAllergens.includes(allergen))
}

export const CATEGORY_LABELS = {
  HOT_COFFEE: 'Sıcak kahveler',
  COLD_COFFEE: 'Soğuk kahveler',
  TEA: 'Çaylar',
  OTHER: 'Diğer',
}

export const labelOf = (list, value) => list.find((option) => option.value === value)?.label ?? value

/** Türk GSM numarasını backend'in beklediği 10 haneye çevirir; geçersizse null. */
export function normalizePhone(input) {
  let digits = input.replace(/\D/g, '')
  if (digits.length === 12 && digits.startsWith('90')) digits = digits.slice(2)
  if (digits.length === 11 && digits.startsWith('0')) digits = digits.slice(1)
  return /^5\d{9}$/.test(digits) ? digits : null
}
