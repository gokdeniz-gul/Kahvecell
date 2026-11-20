/** Dükkân filtreleri (case 3.3): mesafe, puan, açık/kapalı ve sıralama. */

import { DEFAULT_FILTERS, RADIUS_OPTIONS, RATING_OPTIONS, SORT_OPTIONS } from '../lib/shopFilters'

function Select({ id, label, value, options, onChange }) {
  return (
    <label className="filter-select" htmlFor={id}>
      <span className="visually-hidden">{label}</span>
      <select id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  )
}

export default function ShopFilters({ filters, onChange }) {
  const set = (field) => (value) => onChange({ ...filters, [field]: value })
  const isFiltered = filters.openNow || filters.radiusKm || filters.minRating

  return (
    <div className="filters" role="group" aria-label="Dükkân filtreleri">
      <button type="button" className="toggle" aria-pressed={filters.openNow} onClick={() => set('openNow')(!filters.openNow)}>
        ● Şu an açık
      </button>
      <Select id="filter-radius" label="Mesafe" value={filters.radiusKm} options={RADIUS_OPTIONS} onChange={set('radiusKm')} />
      <Select id="filter-rating" label="Puan" value={filters.minRating} options={RATING_OPTIONS} onChange={set('minRating')} />
      <Select id="filter-sort" label="Sıralama" value={filters.sort} options={SORT_OPTIONS} onChange={set('sort')} />
      {isFiltered && (
        <button type="button" className="link-btn subtle" onClick={() => onChange(DEFAULT_FILTERS)}>
          Filtreleri temizle
        </button>
      )}
    </div>
  )
}
