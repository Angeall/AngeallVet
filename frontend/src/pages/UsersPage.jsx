import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

const roleLabels = {
  admin: 'Administrateur', veterinarian: 'Veterinaire',
  assistant: 'ASV', accountant: 'Comptable', guest: 'Invite',
};
const roleColors = {
  admin: 'red', veterinarian: 'green', assistant: 'blue', accountant: 'purple', guest: 'gray',
};

const permissionModules = [
  'dashboard', 'clients', 'animals', 'agenda', 'waiting_room', 'medical',
  'inventory', 'invoices', 'estimates', 'sales', 'hospitalization',
  'communications', 'users', 'stats',
];

const permissionLabels = {
  dashboard: 'Tableau de bord', clients: 'Clients', animals: 'Animaux',
  agenda: 'Agenda', waiting_room: "Salle d'attente", medical: 'Dossiers medicaux',
  inventory: 'Stocks & Pharmacie', invoices: 'Factures', estimates: 'Devis',
  sales: 'Vente comptoir', hospitalization: 'Hospitalisation',
  communications: 'Communications', users: 'Utilisateurs', stats: 'Statistiques',
};

// Fallback defaults matching backend DEFAULT_PERMISSIONS
const DEFAULT_PERMISSIONS = {
  admin: Object.fromEntries(permissionModules.map(m => [m, true])),
  veterinarian: Object.fromEntries(permissionModules.map(m => [m, m !== 'users'])),
  assistant: Object.fromEntries(permissionModules.map(m => [m, m !== 'users' && m !== 'medical' && m !== 'stats'])),
  accountant: Object.fromEntries(permissionModules.map(m => [m, ['dashboard', 'clients', 'inventory', 'invoices', 'estimates', 'sales', 'stats'].includes(m)])),
  guest: Object.fromEntries(permissionModules.map(m => [m, ['dashboard', 'agenda', 'waiting_room'].includes(m)])),
};

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [tab, setTab] = useState('users');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    email: '', password: '', first_name: '', last_name: '', role: 'assistant', phone: '',
  });

  // RBAC state
  const [editingPerms, setEditingPerms] = useState({});
  const [permsDirty, setPermsDirty] = useState({});

  const loadUsers = async () => {
    try {
      const res = await authAPI.listUsers();
      setUsers(res.data);
    } catch {}
  };

  const loadPermissions = async () => {
    try {
      const res = await authAPI.listPermissions();
      const edits = { ...DEFAULT_PERMISSIONS };
      res.data.forEach(p => { edits[p.role] = { ...DEFAULT_PERMISSIONS[p.role], ...p.permissions }; });
      setEditingPerms(edits);
      setPermsDirty({});
    } catch {
      // API failed — use hardcoded defaults so the matrix still renders
      setEditingPerms({ ...DEFAULT_PERMISSIONS });
      setPermsDirty({});
    }
  };

  useEffect(() => {
    loadUsers();
    loadPermissions();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await authAPI.register(form);
      toast.success('Utilisateur cree');
      setShowForm(false);
      setForm({ email: '', password: '', first_name: '', last_name: '', role: 'assistant', phone: '' });
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const toggleActive = async (userId, isActive) => {
    try {
      await authAPI.updateUser(userId, { is_active: !isActive });
      toast.success('Statut mis a jour');
      loadUsers();
    } catch {
      toast.error('Erreur');
    }
  };

  const changeRole = async (userId, newRole) => {
    try {
      await authAPI.updateUser(userId, { role: newRole });
      toast.success('Role mis a jour');
      loadUsers();
    } catch {
      toast.error('Erreur');
    }
  };

  const togglePermission = (role, perm) => {
    setEditingPerms(prev => {
      const current = prev[role] || DEFAULT_PERMISSIONS[role] || {};
      return { ...prev, [role]: { ...current, [perm]: !current[perm] } };
    });
    setPermsDirty(prev => ({ ...prev, [role]: true }));
  };

  const savePermissions = async (role) => {
    try {
      await authAPI.updatePermissions(role, { permissions: editingPerms[role] });
      toast.success(`Permissions ${roleLabels[role]} sauvegardees`);
      setPermsDirty(prev => ({ ...prev, [role]: false }));
    } catch {
      toast.error('Erreur');
    }
  };

  if (currentUser?.role !== 'admin') {
    return (
      <div className="empty-state">
        <h3>Acces restreint</h3>
        <p>Seuls les administrateurs peuvent gerer les utilisateurs.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Utilisateurs & Roles</h1>
        </div>
        <div className="page-header-actions">
          {tab === 'users' && (
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouvel utilisateur</button>
          )}
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'users' ? 'tab active' : 'tab'} onClick={() => setTab('users')}>Utilisateurs</button>
        <button className={tab === 'roles' ? 'tab active' : 'tab'} onClick={() => setTab('roles')}>Permissions par role</button>
      </div>

      {tab === 'users' && (
        <>
          {showForm && (
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouvel utilisateur</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Prenom *</label>
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
                    <label className="form-label">Role *</label>
                    <select className="form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                      {Object.entries(roleLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Telephone</label>
                    <input className="form-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Creer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <div className="card">
            <table>
              <thead><tr><th>Nom</th><th>Email</th><th>Role</th><th>Actif</th><th>Actions</th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td><strong>{u.last_name} {u.first_name}</strong></td>
                    <td>{u.email}</td>
                    <td>
                      <select
                        className="form-select"
                        value={u.role}
                        onChange={(e) => changeRole(u.id, e.target.value)}
                        style={{ width: 'auto', display: 'inline', padding: '4px 8px', fontSize: '0.85rem' }}
                      >
                        {Object.entries(roleLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </td>
                    <td><span className={`badge badge-${u.is_active ? 'green' : 'red'}`}>{u.is_active ? 'Actif' : 'Inactif'}</span></td>
                    <td>
                      <button className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`} onClick={() => toggleActive(u.id, u.is_active)}>
                        {u.is_active ? 'Desactiver' : 'Activer'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'roles' && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Matrice des permissions</h3>
          <p style={{ color: 'var(--gray-500)', marginBottom: '16px', fontSize: '0.85rem' }}>
            Cochez ou decochez les modules accessibles pour chaque role. Les modifications sont sauvegardees par role.
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th style={{ position: 'sticky', left: 0, background: 'white', zIndex: 1 }}>Module</th>
                  {Object.entries(roleLabels).map(([role, label]) => (
                    <th key={role} style={{ textAlign: 'center' }}>
                      <span className={`badge badge-${roleColors[role]}`}>{label}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(permissionLabels).map(([perm, label]) => (
                  <tr key={perm}>
                    <td style={{ position: 'sticky', left: 0, background: 'white', fontWeight: 500 }}>{label}</td>
                    {Object.keys(roleLabels).map((role) => (
                      <td key={role} style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={editingPerms[role]?.[perm] || false}
                          onChange={() => togglePermission(role, perm)}
                          style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
            {Object.keys(roleLabels).map((role) => (
              <button
                key={role}
                className={`btn ${permsDirty[role] ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => savePermissions(role)}
                disabled={!permsDirty[role]}
              >
                Sauver {roleLabels[role]}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
