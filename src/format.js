export function formatPrice(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return value
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(amount)
}

export function intervalLabel(value) {
  if (value === 'monthly') return 'Monthly'
  if (value === 'quarterly') return 'Quarterly'
  if (value === 'yearly') return 'Yearly'
  return value
}
