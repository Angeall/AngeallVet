import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { billingAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function DebtsPage() {
  const [debts, setDebts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    billingAPI.listDebts()
      .then(res => setDebts(res.data))
      .catch(() => toast.error('Erreur de chargement des dettes'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = debts.filter(d => {
    const term = search.toLowerCase();
    return `${d.last_name} ${d.first_name}`.toLowerCase().includes(term)
      || (d.email || '').toLowerCase().includes(term)
      || (d.phone || '').includes(term);
  });

  const totalOutstanding = filtered.reduce((s, d) => s + d.outstanding, 0);

  if (loading) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Dettes clients</h1>
          <span style={{ color: 'var(--gray-400)', fontSize: '0.85rem' }}>
            {filtered.length} client{filtered.length > 1 ? 's' : ''} avec solde impaye
          </span>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon red">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
          </div>
          <div>
            <div className="stat-value" style={{ color: 'var(--red, #ef4444)' }}>{totalOutstanding.toFixed(2)} EUR</div>
            <div className="stat-label">Total impaye</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
          </div>
          <div>
            <div className="stat-value">{filtered.length}</div>
            <div className="stat-label">Clients debiteurs</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 2v20l3-2 3 2 3-2 3 2 3-2 3 2V2l-3 2-3-2-3 2-3-2-3 2-3-2z" /><line x1="8" y1="10" x2="16" y2="10" /><line x1="8" y1="14" x2="16" y2="14" /></svg>
          </div>
          <div>
            <div className="stat-value">{filtered.reduce((s, d) => s + d.invoice_count, 0)}</div>
            <div className="stat-label">Factures impayees</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 className="card-title" style={{ margin: 0 }}>Clients par montant impaye decroissant</h3>
          <input
            type="text"
            className="form-input"
            placeholder="Rechercher un client..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: '250px' }}
          />
        </div>

        <table>
          <thead>
            <tr>
              <th>Client</th>
              <th>Contact</th>
              <th style={{ textAlign: 'center' }}>Factures</th>
              <th style={{ textAlign: 'right' }}>Total du</th>
              <th style={{ textAlign: 'right' }}>Deja paye</th>
              <th style={{ textAlign: 'right' }}>Reste a payer</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(d => {
              const pct = d.total_due > 0 ? (d.total_paid / d.total_due) * 100 : 0;
              return (
                <tr key={d.client_id}>
                  <td>
                    <Link to={`/clients/${d.client_id}`} className="table-link" style={{ fontWeight: 600 }}>
                      {d.last_name} {d.first_name}
                    </Link>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.85rem' }}>{d.email || '-'}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{d.phone || ''}</div>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span className="badge badge-blue">{d.invoice_count}</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>{d.total_due.toFixed(2)} EUR</td>
                  <td style={{ textAlign: 'right' }}>
                    <div>{d.total_paid.toFixed(2)} EUR</div>
                    <div style={{
                      width: '60px', height: '4px', background: 'var(--gray-100)',
                      borderRadius: '2px', marginTop: '4px', marginLeft: 'auto',
                    }}>
                      <div style={{
                        width: `${Math.min(100, pct)}%`, height: '100%',
                        background: pct > 75 ? '#10b981' : pct > 40 ? '#f59e0b' : '#ef4444',
                        borderRadius: '2px',
                      }} />
                    </div>
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--red, #ef4444)', fontSize: '1rem' }}>
                    {d.outstanding.toFixed(2)} EUR
                  </td>
                  <td>
                    <Link to={`/invoices?client_id=${d.client_id}&status=unpaid`} className="btn btn-secondary btn-sm">
                      Voir factures
                    </Link>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan="7" className="table-empty">
                  {search ? 'Aucun client correspondant' : 'Aucune dette en cours'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
