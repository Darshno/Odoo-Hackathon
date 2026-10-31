import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import api from './api'
import {
  activateSubscription,
  createSubscriptionFromQuotation,
  getSubscription,
  listSubscriptions,
  processDueSubscriptions,
} from './subscriptions'

describe('subscription API client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lists subscriptions with query parameters', async () => {
    api.get.mockResolvedValue({ data: { items: [] } })

    await listSubscriptions({ page: 2, page_size: 10, status: 'ACTIVE' })

    expect(api.get).toHaveBeenCalledWith('/subscriptions', {
      params: { page: 2, page_size: 10, status: 'ACTIVE' },
    })
  })

  it('calls the conversion and lifecycle endpoints', async () => {
    api.get.mockResolvedValue({ data: { id: 7 } })
    api.post.mockResolvedValue({ data: { id: 8 } })

    await getSubscription(7)
    await createSubscriptionFromQuotation(12)
    await activateSubscription(8)
    await processDueSubscriptions()

    expect(api.get).toHaveBeenCalledWith('/subscriptions/7')
    expect(api.post).toHaveBeenCalledWith('/subscriptions/from-quotation/12')
    expect(api.post).toHaveBeenCalledWith('/subscriptions/8/activate')
    expect(api.post).toHaveBeenCalledWith('/subscriptions/process-due')
  })
})
