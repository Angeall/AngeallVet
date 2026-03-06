import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  listUsers: () => api.get('/auth/users'),
  updateUser: (id, data) => api.put(`/auth/users/${id}`, data),
};

// Clients
export const clientsAPI = {
  list: (params) => api.get('/clients', { params }),
  get: (id) => api.get(`/clients/${id}`),
  create: (data) => api.post('/clients', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
  merge: (data) => api.post('/clients/merge', data),
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
  addWeight: (id, data) => api.post(`/animals/${id}/weights`, data),
};

// Appointments
export const appointmentsAPI = {
  list: (params) => api.get('/appointments', { params }),
  get: (id) => api.get(`/appointments/${id}`),
  create: (data) => api.post('/appointments', data),
  update: (id, data) => api.put(`/appointments/${id}`, data),
  updateStatus: (id, data) => api.patch(`/appointments/${id}/status`, data),
  cancel: (id) => api.delete(`/appointments/${id}`),
  waitingRoom: () => api.get('/appointments/waiting-room'),
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
};

// Inventory
export const inventoryAPI = {
  listProducts: (params) => api.get('/inventory/products', { params }),
  createProduct: (data) => api.post('/inventory/products', data),
  updateProduct: (id, data) => api.put(`/inventory/products/${id}`, data),
  addLot: (productId, data) => api.post(`/inventory/products/${productId}/lots`, data),
  getExpiring: (days) => api.get('/inventory/expiring', { params: { days } }),
  createMovement: (data) => api.post('/inventory/movements', data),
  getAlerts: () => api.get('/inventory/alerts'),
  listSuppliers: () => api.get('/inventory/suppliers'),
  createSupplier: (data) => api.post('/inventory/suppliers', data),
  createPurchaseOrder: (data) => api.post('/inventory/purchase-orders', data),
};

// Billing
export const billingAPI = {
  listInvoices: (params) => api.get('/billing/invoices', { params }),
  getInvoice: (id) => api.get(`/billing/invoices/${id}`),
  createInvoice: (data) => api.post('/billing/invoices', data),
  listUnpaid: () => api.get('/billing/unpaid'),
  recordPayment: (data) => api.post('/billing/payments', data),
  listEstimates: (params) => api.get('/billing/estimates', { params }),
  createEstimate: (data) => api.post('/billing/estimates', data),
  convertEstimateToInvoice: (data) => api.post('/billing/estimates/to-invoice', data),
};

// Communications
export const communicationsAPI = {
  list: (params) => api.get('/communications', { params }),
  send: (data) => api.post('/communications', data),
  listRules: () => api.get('/communications/reminders'),
  createRule: (data) => api.post('/communications/reminders', data),
  updateRule: (id, data) => api.put(`/communications/reminders/${id}`, data),
  deleteRule: (id) => api.delete(`/communications/reminders/${id}`),
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

export default api;
