import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';

// Pages are code-split per route: each lazy chunk (and its heavy deps, e.g.
// recharts on Stats, FullCalendar on Agenda) loads only when its route opens.
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ClientsPage = lazy(() => import('./pages/ClientsPage'));
const ClientDetailPage = lazy(() => import('./pages/ClientDetailPage'));
const AnimalsPage = lazy(() => import('./pages/AnimalsPage'));
const AnimalDetailPage = lazy(() => import('./pages/AnimalDetailPage'));
const AgendaPage = lazy(() => import('./pages/AgendaPage'));
const WaitingRoomPage = lazy(() => import('./pages/WaitingRoomPage'));
const MedicalRecordsPage = lazy(() => import('./pages/MedicalRecordsPage'));
const InventoryPage = lazy(() => import('./pages/InventoryPage'));
const ProductDetailPage = lazy(() => import('./pages/ProductDetailPage'));
const InvoicesPage = lazy(() => import('./pages/InvoicesPage'));
const InvoiceDetailPage = lazy(() => import('./pages/InvoiceDetailPage'));
const EstimatesPage = lazy(() => import('./pages/EstimatesPage'));
const EstimateDetailPage = lazy(() => import('./pages/EstimateDetailPage'));
const CommunicationsPage = lazy(() => import('./pages/CommunicationsPage'));
const HospitalizationPage = lazy(() => import('./pages/HospitalizationPage'));
const HospitalizationDetailPage = lazy(() => import('./pages/HospitalizationDetailPage'));
const SalesPage = lazy(() => import('./pages/SalesPage'));
const StatsPage = lazy(() => import('./pages/StatsPage'));
const DebtsPage = lazy(() => import('./pages/DebtsPage'));
const UsersPage = lazy(() => import('./pages/UsersPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const BillingRulesPage = lazy(() => import('./pages/BillingRulesPage'));
const AccountingPage = lazy(() => import('./pages/AccountingPage'));
const ControlledSubstancesPage = lazy(() => import('./pages/ControlledSubstancesPage'));
const AssociationsPage = lazy(() => import('./pages/AssociationsPage'));

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-content">Chargement...</div>;
  return user ? children : <Navigate to="/login" />;
}

function App() {
  return (
    <>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Suspense fallback={<div className="page-content">Chargement...</div>}>
                  <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/clients" element={<ClientsPage />} />
                    <Route path="/clients/:id" element={<ClientDetailPage />} />
                    <Route path="/animals" element={<AnimalsPage />} />
                    <Route path="/animals/:id" element={<AnimalDetailPage />} />
                    <Route path="/agenda" element={<AgendaPage />} />
                    <Route path="/waiting-room" element={<WaitingRoomPage />} />
                    <Route path="/medical" element={<MedicalRecordsPage />} />
                    <Route path="/inventory" element={<InventoryPage />} />
                    <Route path="/inventory/:id" element={<ProductDetailPage />} />
                    <Route path="/invoices" element={<InvoicesPage />} />
                    <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
                    <Route path="/estimates" element={<EstimatesPage />} />
                    <Route path="/estimates/:id" element={<EstimateDetailPage />} />
                    <Route path="/communications" element={<CommunicationsPage />} />
                    <Route path="/hospitalization" element={<HospitalizationPage />} />
                    <Route path="/hospitalization/:id" element={<HospitalizationDetailPage />} />
                    <Route path="/sales" element={<SalesPage />} />
                    <Route path="/debts" element={<DebtsPage />} />
                    <Route path="/stats" element={<StatsPage />} />
                    <Route path="/users" element={<UsersPage />} />
                    <Route path="/controlled-substances" element={<ControlledSubstancesPage />} />
                    <Route path="/associations" element={<AssociationsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/billing-rules" element={<BillingRulesPage />} />
                    <Route path="/accounting" element={<AccountingPage />} />
                  </Routes>
                </Suspense>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </>
  );
}

export default App;
