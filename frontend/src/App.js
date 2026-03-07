import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ClientsPage from './pages/ClientsPage';
import ClientDetailPage from './pages/ClientDetailPage';
import AnimalsPage from './pages/AnimalsPage';
import AnimalDetailPage from './pages/AnimalDetailPage';
import AgendaPage from './pages/AgendaPage';
import WaitingRoomPage from './pages/WaitingRoomPage';
import MedicalRecordsPage from './pages/MedicalRecordsPage';
import InventoryPage from './pages/InventoryPage';
import ProductDetailPage from './pages/ProductDetailPage';
import InvoicesPage from './pages/InvoicesPage';
import InvoiceDetailPage from './pages/InvoiceDetailPage';
import EstimatesPage from './pages/EstimatesPage';
import EstimateDetailPage from './pages/EstimateDetailPage';
import CommunicationsPage from './pages/CommunicationsPage';
import HospitalizationPage from './pages/HospitalizationPage';
import UsersPage from './pages/UsersPage';

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
                  <Route path="/users" element={<UsersPage />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </>
  );
}

export default App;
