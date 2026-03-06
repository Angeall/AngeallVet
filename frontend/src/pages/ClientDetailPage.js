import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clientsAPI, animalsAPI, billingAPI, communicationsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function ClientDetailPage() {
  const { id } = useParams();
  const [client, setClient] = useState(null);
  const [animals, setAnimals] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [comms, setComms] = useState([]);
  const [tab, setTab] = useState('animals');

  useEffect(() => {
    async function load() {
      try {
        const [cRes, aRes, iRes, commRes] = await Promise.all([
          clientsAPI.get(id),
          animalsAPI.list({ client_id: id }),
          billingAPI.listInvoices({ client_id: id }),
          communicationsAPI.list({ client_id: id }),
        ]);
        setClient(cRes.data);
        setAnimals(aRes.data);
        setInvoices(iRes.data);
        setComms(commRes.data);
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, [id]);

  if (!client) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <Link to="/clients" style={{ color: 'var(--gray-400)', textDecoration: 'none', fontSize: '0.85rem' }}>
            Clients /
          </Link>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>
            {client.last_name} {client.first_name}
          </h1>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">🐾</div>
          <div><div className="stat-value">{animals.length}</div><div className="stat-label">Animaux</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">🧾</div>
          <div><div className="stat-value">{invoices.length}</div><div className="stat-label">Factures</div></div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${parseFloat(client.account_balance) < 0 ? 'red' : 'green'}`}>💰</div>
          <div>
            <div className="stat-value">{parseFloat(client.account_balance || 0).toFixed(2)}</div>
            <div className="stat-label">Solde (EUR)</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Coordonnées</h3>
        <div className="form-row" style={{ marginTop: '12px' }}>
          <div><strong>Email:</strong> {client.email || '-'}</div>
          <div><strong>Tél:</strong> {client.phone || '-'}</div>
          <div><strong>Mobile:</strong> {client.mobile || '-'}</div>
        </div>
        <div style={{ marginTop: '8px' }}>
          <strong>Adresse:</strong> {client.address} {client.postal_code} {client.city}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {['animals', 'invoices', 'communications'].map((t) => (
          <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-secondary'} btn-sm`} onClick={() => setTab(t)}>
            {t === 'animals' ? 'Animaux' : t === 'invoices' ? 'Factures' : 'Communications'}
          </button>
        ))}
      </div>

      {tab === 'animals' && (
        <div className="card">
          <table>
            <thead><tr><th>Nom</th><th>Espèce</th><th>Race</th><th>Sexe</th><th>Puce</th></tr></thead>
            <tbody>
              {animals.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/animals/${a.id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>{a.name}</Link></td>
                  <td>{a.species}</td>
                  <td>{a.breed || '-'}</td>
                  <td>{a.sex}</td>
                  <td>{a.microchip_number || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'invoices' && (
        <div className="card">
          <table>
            <thead><tr><th>N°</th><th>Date</th><th>Total</th><th>Statut</th></tr></thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.invoice_number}</td>
                  <td>{inv.issue_date}</td>
                  <td>{parseFloat(inv.total).toFixed(2)} EUR</td>
                  <td><span className={`badge badge-${inv.status === 'paid' ? 'green' : inv.status === 'overdue' ? 'red' : 'amber'}`}>{inv.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'communications' && (
        <div className="card">
          <table>
            <thead><tr><th>Date</th><th>Canal</th><th>Sujet</th><th>Statut</th></tr></thead>
            <tbody>
              {comms.map((c) => (
                <tr key={c.id}>
                  <td>{new Date(c.created_at).toLocaleDateString('fr-FR')}</td>
                  <td><span className="badge badge-blue">{c.channel}</span></td>
                  <td>{c.subject || '-'}</td>
                  <td><span className={`badge badge-${c.status === 'sent' ? 'green' : 'amber'}`}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
