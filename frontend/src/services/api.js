import axios from 'axios';
import { pb } from './pocketbase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// --- Application JWT store -------------------------------------------------
// The backend mints a per-tenant application JWT after verifying the PocketBase
// token (see /auth/session). That JWT is what we send to the API.
const APP_TOKEN_KEY = 'app_token';
let appToken = localStorage.getItem(APP_TOKEN_KEY);

export function setAppToken(token) {
  appToken = token || null;
  if (token) localStorage.setItem(APP_TOKEN_KEY, token);
  else localStorage.removeItem(APP_TOKEN_KEY);
}

export function getAppToken() {
  return appToken;
}

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach the application JWT to every request.
api.interceptors.request.use((config) => {
  if (appToken) config.headers.Authorization = `Bearer ${appToken}`;
  return config;
});

// On 401 for a non-auth endpoint, try once to re-exchange the (still valid)
// PocketBase session for a fresh application JWT; otherwise sign out.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {};
    const url = config.url || '';
    const isAuthEndpoint = url.includes('/auth/');
    if (error.response?.status === 401 && !isAuthEndpoint && !config._retry) {
      if (pb.authStore.isValid) {
        try {
          const { data } = await api.post('/auth/session', { pb_token: pb.authStore.token });
          setAppToken(data.access_token);
          config._retry = true;
          config.headers = { ...config.headers, Authorization: `Bearer ${data.access_token}` };
          return api(config);
        } catch (_) {
          // fall through to sign-out
        }
      }
      // Hors ligne : ne pas déconnecter sur un 401 transitoire — on garde la
      // session pour la reprise au retour du réseau.
      if (!navigator.onLine) return Promise.reject(error);
      setAppToken(null);
      pb.authStore.clear();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Config axios portant la clé d'idempotence pour les écritures rejouables hors
// ligne (dédupliquées côté serveur). Voir services/mutations.js.
const idem = (key) => (key ? { headers: { 'Idempotency-Key': key } } : undefined);

// Auth (PocketBase handles credentials; backend issues the application JWT)
export const authAPI = {
  session: (pbToken) => api.post('/auth/session', { pb_token: pbToken }),
  me: () => api.get('/auth/me'),
  modules: () => api.get('/auth/modules'),
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
  create: (data, idempotencyKey) => api.post('/clients', data, idem(idempotencyKey)),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
  merge: (data) => api.post('/clients/merge', data),
  addAlert: (id, data) => api.post(`/clients/${id}/alerts`, data),
  removeAlert: (id, alertId) => api.delete(`/clients/${id}/alerts/${alertId}`),
  listNotes: (id, params) => api.get(`/clients/${id}/notes`, { params }),
  addNote: (id, data) => api.post(`/clients/${id}/notes`, data),
  deleteNote: (id, noteId) => api.delete(`/clients/${id}/notes/${noteId}`),
};

// Animals
export const animalsAPI = {
  list: (params) => api.get('/animals', { params }),
  get: (id) => api.get(`/animals/${id}`),
  create: (data, idempotencyKey) => api.post('/animals', data, idem(idempotencyKey)),
  update: (id, data) => api.put(`/animals/${id}`, data),
  addAlert: (id, data, idempotencyKey) => api.post(`/animals/${id}/alerts`, data, idem(idempotencyKey)),
  removeAlert: (id, alertId) => api.delete(`/animals/${id}/alerts/${alertId}`),
  getWeights: (id) => api.get(`/animals/${id}/weights`),
  getLatestWeight: (id) => api.get(`/animals/${id}/weights/latest`),
  addWeight: (id, data, idempotencyKey) =>
    api.post(`/animals/${id}/weights`, data, idempotencyKey ? { headers: { 'Idempotency-Key': idempotencyKey } } : undefined),
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
  create: (data, idempotencyKey) => api.post('/appointments', data, idem(idempotencyKey)),
  update: (id, data) => api.put(`/appointments/${id}`, data),
  updateStatus: (id, data) => api.patch(`/appointments/${id}/status`, data),
  cancel: (id) => api.delete(`/appointments/${id}`),
  waitingRoom: (params) => api.get('/appointments/waiting-room', { params }),
};

// Agenda — personal iCal feed + Google Calendar two-way sync (google_calendar module)
export const agendaAPI = {
  icalStatus: () => api.get('/agenda/ical'),
  icalEnable: () => api.post('/agenda/ical/enable'),
  icalRotate: () => api.post('/agenda/ical/rotate'),
  icalDisable: () => api.delete('/agenda/ical'),
  // Google OAuth (two-way)
  googleStatus: () => api.get('/agenda/google/status'),
  googleConnect: () => api.get('/agenda/google/connect'),
  googleSync: () => api.post('/agenda/google/sync'),
  googleDisconnect: () => api.delete('/agenda/google'),
  externalEvents: (params) => api.get('/agenda/external-events', { params }),
  // Sync conflicts
  listConflicts: () => api.get('/agenda/conflicts'),
  resolveConflict: (id, resolution) => api.post(`/agenda/conflicts/${id}/resolve`, { resolution }),
};

// Medical Records
export const medicalAPI = {
  listRecords: (params) => api.get('/medical/records', { params }),
  getRecord: (id) => api.get(`/medical/records/${id}`),
  createRecord: (data, idempotencyKey) =>
    api.post('/medical/records', data, idempotencyKey ? { headers: { 'Idempotency-Key': idempotencyKey } } : undefined),
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
  sendInvoice: (id) => api.post(`/billing/invoices/${id}/send`),
  invoicePdf: (id) => api.get(`/billing/invoices/${id}/pdf`, { responseType: 'blob' }),
  estimatePdf: (id) => api.get(`/billing/estimates/${id}/pdf`, { responseType: 'blob' }),
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
  runReminders: () => api.post('/communications/reminders/run'),
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
  create: (data, idempotencyKey) => api.post('/hospitalization', data, idem(idempotencyKey)),
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

// Excel exports
export const exportsAPI = {
  xlsx: (data) => api.post('/export/xlsx', data, { responseType: 'blob' }),
  backup: () => api.get('/export/backup', { responseType: 'blob' }),
};

// Veterinarian commission rules (admin)
export const commissionsAPI = {
  listRules: () => api.get('/billing/rules'),
  createRule: (data) => api.post('/billing/rules', data),
  updateRule: (id, data) => api.put(`/billing/rules/${id}`, data),
  deleteRule: (id) => api.delete(`/billing/rules/${id}`),
  listPrograms: () => api.get('/billing/programs'),
  createProgram: (data) => api.post('/billing/programs', data),
  updateProgram: (id, data) => api.put(`/billing/programs/${id}`, data),
  deleteProgram: (id) => api.delete(`/billing/programs/${id}`),
  listVets: () => api.get('/billing/veterinarians'),
  assignProgram: (userId, programId) => api.put(`/billing/veterinarians/${userId}/program`, { program_id: programId }),
  report: (params) => api.get('/billing/commissions', { params }),
  setDayRule: (data) => api.put('/billing/commissions/day-rule', data),
};

export default api;
