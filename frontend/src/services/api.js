import axios from 'axios';
import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach Supabase access token to every request
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

// Handle 401 – sign out only for non-auth endpoints to avoid
// destroying a valid Supabase session during the login flow.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const url = error.config?.url || '';
    const isAuthEndpoint = url.includes('/auth/');
    if (error.response?.status === 401 && !isAuthEndpoint) {
      await supabase.auth.signOut();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth (backend profile endpoints - Supabase handles actual auth)
export const authAPI = {
  me: () => api.get('/auth/me'),
  updateMe: (data) => api.put('/auth/me', data),
  listUsers: () => api.get('/auth/users'),
  listStaff: () => api.get('/auth/staff'),
  updateUser: (id, data) => api.put(`/auth/users/${id}`, data),
  register: (data) => api.post('/auth/register', data),
  // Permissions
  listPermissions: () => api.get('/auth/permissions'),
  myPermissions: () => api.get('/auth/permissions/me'),
  updatePermissions: (role, data) => api.put(`/auth/permissions/${role}`, data),
  // Notifications
  listNotifications: (params) => api.get('/auth/notifications', { params }),
  unreadCount: () => api.get('/auth/notifications/unread-count'),
  markRead: (id) => api.patch(`/auth/notifications/${id}/read`),
  markAllRead: () => api.patch('/auth/notifications/read-all'),
};

// Clients
export const clientsAPI = {
  list: (params) => api.get('/clients', { params }),
  get: (id) => api.get(`/clients/${id}`),
  create: (data) => api.post('/clients', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
  merge: (data) => api.post('/clients/merge', data),
  addAlert: (id, data) => api.post(`/clients/${id}/alerts`, data),
  removeAlert: (id, alertId) => api.delete(`/clients/${id}/alerts/${alertId}`),
};

// Animals
export const animalsAPI = {
  list: (params) => api.get('/animals', { params }),
  get: (id) => api.get(`/animals/${id}`),
  create: (data) => api.post('/animals', data),
  update: (id, data) => api.put(`/animals/${id}`, data),
  addAlert: (id, data) => api.post(`/animals/${id}/alerts`, data),
  removeAlert: (id, alertId) => api.delete(`/animals/${id}/alerts/${alertId}`),
  getWeights: (id) => api.get(`/animals/${id}/weights`),
  getLatestWeight: (id) => api.get(`/animals/${id}/weights/latest`),
  addWeight: (id, data) => api.post(`/animals/${id}/weights`, data),
  // Species
  listSpecies: () => api.get('/animals/species'),
  createSpecies: (data) => api.post('/animals/species', data),
  updateSpecies: (id, data) => api.put(`/animals/species/${id}`, data),
  deleteSpecies: (id) => api.delete(`/animals/species/${id}`),
};

// Appointments
export const appointmentsAPI = {
  list: (params) => api.get('/appointments', { params }),
  get: (id) => api.get(`/appointments/${id}`),
  create: (data) => api.post('/appointments', data),
  update: (id, data) => api.put(`/appointments/${id}`, data),
  updateStatus: (id, data) => api.patch(`/appointments/${id}/status`, data),
  cancel: (id) => api.delete(`/appointments/${id}`),
  waitingRoom: (params) => api.get('/appointments/waiting-room', { params }),
};

// Medical Records
export const medicalAPI = {
  listRecords: (params) => api.get('/medical/records', { params }),
  getRecord: (id) => api.get(`/medical/records/${id}`),
  createRecord: (data) => api.post('/medical/records', data),
  uploadAttachment: (recordId, formData) =>
    api.post(`/medical/records/${recordId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  listTemplates: (params) => api.get('/medical/templates', { params }),
  createTemplate: (data) => api.post('/medical/templates', data),
  getTemplate: (id) => api.get(`/medical/templates/${id}`),
  updateTemplate: (id, data) => api.put(`/medical/templates/${id}`, data),
  deleteTemplate: (id) => api.delete(`/medical/templates/${id}`),
  createInvoiceFromRecord: (recordId) => api.post(`/medical/records/${recordId}/create-invoice`),
};

// Inventory
export const inventoryAPI = {
  listProducts: (params) => api.get('/inventory/products', { params }),
  getProduct: (id) => api.get(`/inventory/products/${id}`),
  createProduct: (data) => api.post('/inventory/products', data),
  updateProduct: (id, data) => api.put(`/inventory/products/${id}`, data),
  addLot: (productId, data) => api.post(`/inventory/products/${productId}/lots`, data),
  getExpiring: (days) => api.get('/inventory/expiring', { params: { days } }),
  createMovement: (data) => api.post('/inventory/movements', data),
  getAlerts: () => api.get('/inventory/alerts'),
  listSuppliers: () => api.get('/inventory/suppliers'),
  createSupplier: (data) => api.post('/inventory/suppliers', data),
  createPurchaseOrder: (data) => api.post('/inventory/purchase-orders', data),
  getShortcuts: () => api.get('/inventory/shortcuts'),
};

// Billing
export const billingAPI = {
  listInvoices: (params) => api.get('/billing/invoices', { params }),
  getInvoice: (id) => api.get(`/billing/invoices/${id}`),
  createInvoice: (data) => api.post('/billing/invoices', data),
  listUnpaid: () => api.get('/billing/unpaid'),
  recordPayment: (data) => api.post('/billing/payments', data),
  listEstimates: (params) => api.get('/billing/estimates', { params }),
  getEstimate: (id) => api.get(`/billing/estimates/${id}`),
  createEstimate: (data) => api.post('/billing/estimates', data),
  convertEstimateToInvoice: (data) => api.post('/billing/estimates/to-invoice', data),
  getStats: (params) => api.get('/billing/stats', { params }),
  listDebts: () => api.get('/billing/debts'),
  getDebtAcknowledgment: (id) => api.get(`/billing/invoices/${id}/debt-acknowledgment`),
  addInvoiceVet: (invoiceId, userId) => api.post(`/billing/invoices/${invoiceId}/veterinarians?user_id=${userId}`),
  removeInvoiceVet: (invoiceId, userId) => api.delete(`/billing/invoices/${invoiceId}/veterinarians/${userId}`),
};

// Communications
export const communicationsAPI = {
  list: (params) => api.get('/communications', { params }),
  send: (data) => api.post('/communications', data),
  listRules: () => api.get('/communications/reminders'),
  createRule: (data) => api.post('/communications/reminders', data),
  updateRule: (id, data) => api.put(`/communications/reminders/${id}`, data),
  deleteRule: (id) => api.delete(`/communications/reminders/${id}`),
  postalDueReminders: () => api.get('/communications/reminders/postal-due'),
};

// Settings
export const settingsAPI = {
  getClinic: () => api.get('/settings/clinic'),
  updateClinic: (data) => api.put('/settings/clinic', data),
  getVatRates: () => api.get('/settings/vat-rates'),
  createVatRate: (data) => api.post('/settings/vat-rates', data),
  updateVatRate: (id, data) => api.put(`/settings/vat-rates/${id}`, data),
  deleteVatRate: (id) => api.delete(`/settings/vat-rates/${id}`),
};

// Hospitalization
export const hospitalizationAPI = {
  list: (params) => api.get('/hospitalization', { params }),
  get: (id) => api.get(`/hospitalization/${id}`),
  create: (data) => api.post('/hospitalization', data),
  update: (id, data) => api.put(`/hospitalization/${id}`, data),
  addTask: (hospId, data) => api.post(`/hospitalization/${hospId}/tasks`, data),
  updateTask: (hospId, taskId, data) =>
    api.patch(`/hospitalization/${hospId}/tasks/${taskId}`, data),
};

// Associations
export const associationsAPI = {
  list: () => api.get('/associations'),
  get: (id) => api.get(`/associations/${id}`),
  create: (data) => api.post('/associations', data),
  update: (id, data) => api.put(`/associations/${id}`, data),
};

// Controlled Substances
export const controlledSubstancesAPI = {
  listRegister: (params) => api.get('/controlled-substances/register', { params }),
  createEntry: (data) => api.post('/controlled-substances/entries', data),
  exportRegister: (params) => api.get('/controlled-substances/register/export', { params, responseType: 'blob' }),
};

export default api;
