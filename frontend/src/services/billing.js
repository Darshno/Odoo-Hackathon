import api from './api'

export const listInvoices = (params = {}) => api.get('/billing/invoices', { params })
export const getInvoice = (id) => api.get(`/billing/invoices/${id}`)
export const generateInvoiceFromSubscription = (subscriptionId, payload = {}) => api.post(`/billing/invoices/generate/${subscriptionId}`, payload)
export const issueInvoice = (id) => api.post(`/billing/invoices/${id}/issue`)
export const voidInvoice = (id) => api.post(`/billing/invoices/${id}/void`)
export const processDueInvoices = () => api.post('/billing/invoices/process-due')

export const listPayments = (params = {}) => api.get('/billing/payments', { params })
export const getPayment = (id) => api.get(`/billing/payments/${id}`)
export const recordPayment = (payload) => api.post('/billing/payments', payload)
export const listDiscounts = () => api.get('/billing/discounts')
export const createDiscount = (payload) => api.post('/billing/discounts', payload)
