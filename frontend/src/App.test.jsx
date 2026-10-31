import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import { validatePassword } from './utils/validation'

describe('Brightloop foundation', () => {
  it('renders the public product promise and CTA', () => {
    render(<MemoryRouter><LandingPage /></MemoryRouter>)
    expect(screen.getByText('Subscriptions,')).toBeInTheDocument()
    expect(screen.getAllByText('Get Started').length).toBeGreaterThan(0)
  })

  it('enforces the password policy client-side', () => {
    expect(validatePassword('weak')).toHaveLength(3)
    expect(validatePassword('StrongPass!1')).toHaveLength(0)
  })
})
