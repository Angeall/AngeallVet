import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    email: '', password: '', first_name: '', last_name: '', role: 'assistant', phone: '',
  });

  useEffect(() => {
    async function load() {
      try {
        const res = await authAPI.listUsers();
        setUsers(res.data);
      } catch {
        // Only admins can see this
      }
    }
    load();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await authAPI.register(form);
      toast.success('Utilisateur créé');
      setShowForm(false);
      const res = await authAPI.listUsers();
      setUsers(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const toggleActive = async (userId, isActive) => {
    try {
      await authAPI.updateUser(userId, { is_active: !isActive });
      toast.success('Statut mis à jour');
      const res = await authAPI.listUsers();
      setUsers(res.data);
    } catch {
      toast.error('Erreur');
    }
  };

  const roleLabels = { admin: 'Administrateur', veterinarian: 'Vétérinaire', assistant: 'ASV', accountant: 'Comptable' };

  if (currentUser?.role !== 'admin') {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🔒</div>
        <h3>Accès restreint</h3>
        <p>Seuls les administrateurs peuvent gérer les utilisateurs.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Utilisateurs (RBAC)</h1>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouvel utilisateur</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
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
                <label className="form-label">Email *</label>
                <input type="email" className="form-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Mot de passe *</label>
                <input type="password" className="form-input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Rôle *</label>
                <select className="form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  {Object.entries(roleLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Téléphone</label>
                <input className="form-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Créer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <table>
          <thead><tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Actif</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td className="table-link">{u.last_name} {u.first_name}</td>
                <td>{u.email}</td>
                <td><span className={`badge badge-${u.role === 'admin' ? 'red' : u.role === 'veterinarian' ? 'green' : u.role === 'accountant' ? 'purple' : 'blue'}`}>{roleLabels[u.role]}</span></td>
                <td><span className={`badge badge-${u.is_active ? 'green' : 'red'}`}>{u.is_active ? 'Actif' : 'Inactif'}</span></td>
                <td>
                  <button className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`} onClick={() => toggleActive(u.id, u.is_active)}>
                    {u.is_active ? 'Désactiver' : 'Activer'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
