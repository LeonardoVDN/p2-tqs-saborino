const brlFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const numFmt = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 })

export function brl(v) {
  const n = Number(v ?? 0)
  return brlFmt.format(Number.isFinite(n) ? n : 0)
}
export function num(v) {
  const n = Number(v ?? 0)
  return numFmt.format(Number.isFinite(n) ? n : 0)
}
export function pct(v) {
  if (v === null || v === undefined) return '—'
  return `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`
}
