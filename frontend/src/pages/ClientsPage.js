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
    address: '', city: '', postal_code: '',
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
      await clientsAPI.create(form);
      toast.success('Client créé');
      setShowForm(false);
      setForm({ first_name: '', last_name: '', email: '', phone: '', mobile: '', address: '', city: '', postal_code: '' });
      load();
    } catch {
      toast.error('Erreur lors de la création');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Clients</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          + Nouveau client
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau client</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Prénom *</label>
                <input className="form-input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Nom *</label>
                <input className="form-input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Email</label>
                <input type="email" className="form-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Téléphone</label>
                <input className="form-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Mobile</label>
                <input className="form-input" value={form.mobile} onChange={(e) => setForm({ ...form, mobile: e.target.value })} />
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
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ marginBottom: '16px' }}>
          <input
            className="form-input"
            placeholder="Rechercher par nom, email, téléphone..."
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
                <th>Téléphone</th>
                <th>Ville</th>
                <th>Animaux</th>
                <th>Solde</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/clients/${c.id}`} style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>
                      {c.last_name} {c.first_name}
                    </Link>
                  </td>
                  <td>{c.email}</td>
                  <td>{c.mobile || c.phone}</td>
                  <td>{c.city}</td>
                  <td><span className="badge badge-blue">{c.animal_count || 0}</span></td>
                  <td>
                    <span className={parseFloat(c.account_balance) < 0 ? 'badge badge-red' : 'badge badge-green'}>
                      {parseFloat(c.account_balance || 0).toFixed(2)} EUR
                    </span>
                  </td>
                </tr>
              ))}
              {clients.length === 0 && (
                <tr><td colSpan="6" style={{ textAlign: 'center', color: 'var(--gray-400)' }}>Aucun client trouvé</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
