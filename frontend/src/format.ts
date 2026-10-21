const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
const one = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1, minimumFractionDigits: 1 })

export const money = (v: number | null | undefined) => (v == null ? '—' : (v < 0 ? '−₹' : '₹') + inr.format(Math.abs(v)))
export const num = (v: number | null | undefined) => (v == null ? '—' : one.format(v))
export const pct = (v: number | null | undefined) => (v == null ? '—' : (v > 0 ? '+' : '') + one.format(v) + '%')
export const tone = (v: number | null | undefined) => (v == null || v === 0 ? '' : v > 0 ? 'up' : 'down')

export function lakhCrore(v: number | null | undefined): string {
  if (v == null) return '—'
  if (v < 0) return '−' + lakhCrore(-v)
  if (v >= 1e7) return '₹' + one.format(v / 1e7) + ' Cr'
  if (v >= 1e5) return '₹' + one.format(v / 1e5) + ' L'
  return money(v)
}

export const SIGNAL_LABEL = { buy: 'Buy', hold: 'Hold', sell: 'Sell' } as const
export const CALL_LABEL = { overweight: 'Overweight', neutral: 'Neutral', underweight: 'Underweight' } as const
