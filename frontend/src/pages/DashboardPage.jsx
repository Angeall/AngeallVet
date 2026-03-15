import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { appointmentsAPI, billingAPI, inventoryAPI, hospitalizationAPI, communicationsAPI } from '../services/api';

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    todayAppointments: 0,
    waitingRoom: [],
    unpaidInvoices: 0,
    stockAlerts: 0,
    activeHospitalizations: 0,
  });

  useEffect(() => {
    async function load() {
      try {
        const today = new Date().toISOString().slice(0, 10);
        const [appts, unpaid, alerts, hosps] = await Promise.all([
          appointmentsAPI.list({ date_from: today, date_to: today }),
          billingAPI.listUnpaid(),
          inventoryAPI.getAlerts(),
          hospitalizationAPI.list({ active_only: true }),
        ]);
        setStats({
          todayAppointments: appts.data.length,
          waitingRoom: appts.data.filter((a) => ['confirmed', 'arrived', 'in_progress'].includes(a.status)),
          unpaidInvoices: unpaid.data.length,
          stockAlerts: alerts.data.length,
          activeHospitalizations: hosps.data.length,
        });
      } catch {
        // Dashboard loads best-effort
      }
    }
    load();
  }, []);

  const printPostalReminders = async () => {
    try {
      const res = await communicationsAPI.postalDueReminders();
      const reminders = res.data;
      if (!reminders || reminders.length === 0) {
        alert('Aucun rappel postal en attente.');
        return;
      }
      const w = window.open('', '_blank');
      const letters = reminders.map(r => {
        const template = r.postal_template || `Madame, Monsieur ${r.client_name},\n\nNous vous rappelons que votre animal ${r.animal_name} (${r.species || ''}) doit recevoir son rappel de vaccination "${r.vaccine_name}".\n\nDate prevue : ${r.due_date}\n\nNous vous invitons a prendre rendez-vous au plus vite.\n\nCordialement,\nVotre clinique veterinaire`;
        return `
          <div style="page-break-after: always; padding: 40px; font-family: serif; font-size: 14px; line-height: 1.6;">
            <div style="text-align: right; margin-bottom: 40px;">
              <strong>${r.client_name}</strong><br/>
              ${r.client_address}<br/>
              ${r.client_postal_code} ${r.client_city}
            </div>
            <div style="margin-bottom: 30px; text-align: right; font-size: 12px; color: #666;">
              Le ${new Date().toLocaleDateString('fr-FR')}
            </div>
            <div style="white-space: pre-wrap;">${template
              .replace(/\{client_name\}/g, r.client_name)
              .replace(/\{animal_name\}/g, r.animal_name)
              .replace(/\{species\}/g, r.species || '')
              .replace(/\{vaccine_name\}/g, r.vaccine_name)
              .replace(/\{due_date\}/g, r.due_date)
            }</div>
          </div>`;
      }).join('');
      w.document.write(`<html><head><title>Rappels postaux</title></head><body>${letters}</body></html>`);
      w.document.close();
      w.print();
    } catch {
      alert('Erreur lors du chargement des rappels postaux.');
    }
  };

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Bonjour' : hour < 18 ? 'Bon apres-midi' : 'Bonsoir';

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{greeting}, {user?.first_name}</h1>
          <p className="page-subtitle">Voici un apercu de votre clinique aujourd'hui</p>
        </div>
      </div>

      <div className="stats-grid">
        <Link to="/agenda" className="stat-card">
          <div className="stat-icon teal">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          </div>
          <div className="stat-info">
            <div className="stat-value">{stats.todayAppointments}</div>
            <div className="stat-label">RDV aujourd'hui</div>
          </div>
        </Link>

        <Link to="/waiting-room" className="stat-card">
          <div className="stat-icon green">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <div className="stat-info">
            <div className="stat-value">{stats.waitingRoom.length}</div>
            <div className="stat-label">En salle d'attente</div>
          </div>
        </Link>

        <Link to="/invoices" className="stat-card">
          <div className="stat-icon amber">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 2v20l3-2 3 2 3-2 3 2 3-2 3 2V2l-3 2-3-2-3 2-3-2-3 2-3-2z"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="16" y2="14"/></svg>
          </div>
          <div className="stat-info">
            <div className="stat-value">{stats.unpaidInvoices}</div>
            <div className="stat-label">Factures impayees</div>
          </div>
        </Link>

        <Link to="/inventory" className="stat-card">
          <div className="stat-icon red">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
          </div>
          <div className="stat-info">
            <div className="stat-value">{stats.stockAlerts}</div>
            <div className="stat-label">Alertes stock</div>
          </div>
        </Link>

        <Link to="/hospitalization" className="stat-card">
          <div className="stat-icon purple">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"/><line x1="12" y1="7" x2="12" y2="13"/><line x1="9" y1="10" x2="15" y2="10"/></svg>
          </div>
          <div className="stat-info">
            <div className="stat-value">{stats.activeHospitalizations}</div>
            <div className="stat-label">Hospitalisations</div>
          </div>
        </Link>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">
          <h3 className="card-title">Rappels vaccins postaux</h3>
          <button className="btn btn-secondary btn-sm" onClick={printPostalReminders}>
            Imprimer les courriers
          </button>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
          Imprime les lettres de rappel vaccination pour les clients configures en canal postal.
        </p>
      </div>

      {stats.waitingRoom.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">Salle d'attente</h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--gray-500)', marginTop: '2px' }}>{stats.waitingRoom.length} patient(s) en attente</p>
            </div>
            <Link to="/waiting-room" className="btn btn-secondary btn-sm">Voir tout</Link>
          </div>
          {stats.waitingRoom.slice(0, 5).map((appt) => (
            <div key={appt.id} className={`waiting-room-card ${appt.status.replace('_', '-')}`}>
              <div className="waiting-room-info">
                <div className="waiting-room-time">
                  {new Date(appt.start_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--gray-800)' }}>
                    {appt.reason || appt.appointment_type}
                  </h4>
                </div>
              </div>
              <span className={`badge badge-${appt.status === 'arrived' ? 'amber' : appt.status === 'in_progress' ? 'green' : 'blue'}`}>
                {appt.status === 'arrived' ? 'Arrive' : appt.status === 'in_progress' ? 'En consultation' : 'Confirme'}
              </span>
            </div>
          ))}
        </div>
      )}

      {stats.waitingRoom.length === 0 && stats.todayAppointments === 0 && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--gray-300)" strokeWidth="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            </div>
            <h3>Journee calme</h3>
            <p>Aucun rendez-vous prevu pour aujourd'hui</p>
          </div>
        </div>
      )}
    </div>
  );
}
