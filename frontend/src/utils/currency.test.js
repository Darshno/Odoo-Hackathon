import { describe, expect, it } from 'vitest'
import { formatCurrency } from './currency'

describe('formatCurrency', () => {
  it('formats amounts with the Indian rupee symbol and Indian grouping', () => {
    expect(formatCurrency('USD', '1234567.5')).toBe('₹12,34,567.50')
  })

  it('supports formatting a value without a currency argument', () => {
    expect(formatCurrency(25)).toBe('₹25.00')
  })
})
