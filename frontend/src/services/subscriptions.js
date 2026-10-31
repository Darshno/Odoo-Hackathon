import api from './api'

export const listSubscriptions = (params = {}) => api.get('/subscriptions', { params })
export const getSubscription = (id) => api.get(`/subscriptions/${id}`)
export const createSubscriptionFromQuotation = (quotationId) => api.post(`/subscriptions/from-quotation/${quotationId}`)
export const activateSubscription = (id) => api.post(`/subscriptions/${id}/activate`)
export const pauseSubscription = (id) => api.post(`/subscriptions/${id}/pause`)
export const resumeSubscription = (id) => api.post(`/subscriptions/${id}/resume`)
export const renewSubscription = (id) => api.post(`/subscriptions/${id}/renew`)
export const closeSubscription = (id) => api.post(`/subscriptions/${id}/close`)
export const processDueSubscriptions = () => api.post('/subscriptions/process-due')
