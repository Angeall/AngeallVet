import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { clientsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '', mobile: '',
    address: '', city: '', postal_code: '', vat_number: '',
  });

  const load = useCallback(async () => {
    try {
      const res = await clientsAPI.list({ search: search || undefined });
      setClients(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Convert empty strings to null so backend validation passes
      const payload = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, v === '' ? null : v])
      );
      await clientsAPI.create(payload);
      toast.success('Client cree');
      setShowForm(false);
      setForm({ first_name: '', last_name: '', email: '', phone: '', mobile: '', address: '', city: '', postal_code: '', vat_number: '' });
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Clients</h1>
          <p className="page-subtitle">{clients.length} client(s) enregistre(s)</p>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Nouveau client
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card" style={{ animation: 'slideUp 0.25s ease' }}>
          <div className="card-header">
            <h3 className="card-title">Nouveau client</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowForm(false)}>Annuler</button>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Prenom <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input className="form-input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Nom <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input className="form-input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Email</label>
                <input type="email" className="form-input" placeholder="email@exemple.fr" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Telephone</label>
                <input className="form-input" placeholder="01 23 45 67 89" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Mobile</label>
                <input className="form-input" placeholder="06 12 34 56 78" value={form.mobile} onChange={(e) => setForm({ ...form, mobile: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Adresse</label>
                <input className="form-input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Ville</label>
                <input className="form-input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Code postal</label>
                <input className="form-input" value={form.postal_code} onChange={(e) => setForm({ ...form, postal_code: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">N TVA (entreprises)</label>
                <input className="form-input" placeholder="FR12345678901" value={form.vat_number} onChange={(e) => setForm({ ...form, vat_number: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ marginBottom: '16px', position: 'relative' }}>
          <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--gray-400)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </span>
          <input
            className="form-input"
            style={{ paddingLeft: '36px' }}
            placeholder="Rechercher par nom, email, telephone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>Email</th>
                <th>Telephone</th>
                <th>Ville</th>
                <th>Animaux</th>
                <th>Solde</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/clients/${c.id}`} className="table-link">
                      {c.last_name} {c.first_name}
                    </Link>
                  </td>
                  <td style={{ color: 'var(--gray-500)' }}>{c.email || '-'}</td>
                  <td>{c.mobile || c.phone || '-'}</td>
                  <td>{c.city || '-'}</td>
                  <td><span className="badge badge-teal">{c.animal_count || 0}</span></td>
                  <td>
                    <span className={`badge ${parseFloat(c.account_balance) < 0 ? 'badge-red' : 'badge-green'}`}>
                      {parseFloat(c.account_balance || 0).toFixed(2)} EUR
                    </span>
                  </td>
                </tr>
              ))}
              {clients.length === 0 && (
                <tr><td colSpan="6" className="table-empty">
                  <span className="table-empty-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--gray-300)" strokeWidth="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  </span>
                  Aucun client trouve
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
