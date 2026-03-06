import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { appointmentsAPI, billingAPI, inventoryAPI, hospitalizationAPI } from '../services/api';

export default function DashboardPage() {
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
          waitingRoom: appts.data.filter((a) =>
            ['confirmed', 'arrived', 'in_progress'].includes(a.status)
          ),
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

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '24px' }}>
        Tableau de bord
      </h1>

      <div className="stats-grid">
        <Link to="/agenda" style={{ textDecoration: 'none' }}>
          <div className="stat-card">
            <div className="stat-icon blue">📅</div>
            <div>
              <div className="stat-value">{stats.todayAppointments}</div>
              <div className="stat-label">RDV aujourd'hui</div>
            </div>
          </div>
        </Link>

        <Link to="/waiting-room" style={{ textDecoration: 'none' }}>
          <div className="stat-card">
            <div className="stat-icon green">🏥</div>
            <div>
              <div className="stat-value">{stats.waitingRoom.length}</div>
              <div className="stat-label">En salle d'attente</div>
            </div>
          </div>
        </Link>

        <Link to="/invoices" style={{ textDecoration: 'none' }}>
          <div className="stat-card">
            <div className="stat-icon amber">🧾</div>
            <div>
              <div className="stat-value">{stats.unpaidInvoices}</div>
              <div className="stat-label">Factures impayées</div>
            </div>
          </div>
        </Link>

        <Link to="/inventory" style={{ textDecoration: 'none' }}>
          <div className="stat-card">
            <div className="stat-icon red">💊</div>
            <div>
              <div className="stat-value">{stats.stockAlerts}</div>
              <div className="stat-label">Alertes stock</div>
            </div>
          </div>
        </Link>

        <Link to="/hospitalization" style={{ textDecoration: 'none' }}>
          <div className="stat-card">
            <div className="stat-icon purple">🛏️</div>
            <div>
              <div className="stat-value">{stats.activeHospitalizations}</div>
              <div className="stat-label">Hospitalisations</div>
            </div>
          </div>
        </Link>
      </div>

      {stats.waitingRoom.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Salle d'attente</h2>
            <Link to="/waiting-room" className="btn btn-secondary btn-sm">Voir tout</Link>
          </div>
          {stats.waitingRoom.slice(0, 5).map((appt) => (
            <div key={appt.id} className={`waiting-room-card ${appt.status.replace('_', '-')}`}>
              <div>
                <strong>
                  {new Date(appt.start_time).toLocaleTimeString('fr-FR', {
                    hour: '2-digit', minute: '2-digit',
                  })}
                </strong>
                {' - '}{appt.reason || appt.appointment_type}
              </div>
              <span className={`badge badge-${appt.status === 'arrived' ? 'amber' : appt.status === 'in_progress' ? 'green' : 'blue'}`}>
                {appt.status === 'arrived' ? 'Arrivé' : appt.status === 'in_progress' ? 'En consultation' : 'Confirmé'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
