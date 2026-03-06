import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const navItems = [
  { section: 'Principal' },
  { path: '/', label: 'Tableau de bord', icon: '📊' },
  { path: '/agenda', label: 'Agenda', icon: '📅' },
  { path: '/waiting-room', label: 'Salle d\'attente', icon: '🏥' },
  { section: 'Patients' },
  { path: '/clients', label: 'Clients', icon: '👤' },
  { path: '/animals', label: 'Animaux', icon: '🐾' },
  { path: '/medical', label: 'Dossiers médicaux', icon: '📋' },
  { path: '/hospitalization', label: 'Hospitalisation', icon: '🛏️' },
  { section: 'Gestion' },
  { path: '/inventory', label: 'Stocks & Pharmacie', icon: '💊' },
  { path: '/invoices', label: 'Factures', icon: '🧾' },
  { path: '/estimates', label: 'Devis', icon: '📝' },
  { section: 'Communication' },
  { path: '/communications', label: 'Communications', icon: '📧' },
  { section: 'Administration' },
  { path: '/users', label: 'Utilisateurs', icon: '👥' },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <a href="/" className="sidebar-logo">
          🐾 AngeallVet
        </a>
        <nav className="sidebar-nav">
          {navItems.map((item, i) =>
            item.section ? (
              <div key={i} className="sidebar-section">{item.section}</div>
            ) : (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                onClick={() => setSidebarOpen(false)}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            )
          )}
        </nav>
      </aside>

      <div className="main-content">
        <header className="header">
          <button
            className="btn btn-secondary btn-sm"
            style={{ display: 'none' }}
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            Menu
          </button>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--gray-600)' }}>
              {user?.first_name} {user?.last_name}
            </span>
            <span className="badge badge-blue">{user?.role}</span>
            <button className="btn btn-secondary btn-sm" onClick={logout}>
              Déconnexion
            </button>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
