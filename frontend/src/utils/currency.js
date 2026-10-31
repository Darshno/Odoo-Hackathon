const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export const formatCurrency = (currencyOrValue, value) => {
  const amount = value === undefined ? currencyOrValue : value
  return inrFormatter.format(Number(amount ?? 0))
}
