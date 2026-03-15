import React, { useState, useEffect } from 'react';
import { associationsAPI } from '../services/api';
import toast from 'react-hot-toast';

const emptyForm = {
  name: '', contact_name: '', email: '', phone: '', address: '',
  discount_percent: '', notes: '',
};

export default function AssociationsPage() {
  const [associations, setAssociations] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [editId, setEditId] = useState(null);

  const load = async () => {
    try {
      const res = await associationsAPI.list();
      setAssociations(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, []);

  const openEdit = (assoc) => {
    setEditId(assoc.id);
    setForm({
      name: assoc.name || '',
      contact_name: assoc.contact_name || '',
      email: assoc.email || '',
      phone: assoc.phone || '',
      address: assoc.address || '',
      discount_percent: assoc.discount_percent ?? '',
      notes: assoc.notes || '',
    });
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      discount_percent: form.discount_percent !== '' ? parseFloat(form.discount_percent) : null,
      email: form.email || null,
      phone: form.phone || null,
      contact_name: form.contact_name || null,
      address: form.address || null,
      notes: form.notes || null,
    };
    try {
      if (editId) {
        await associationsAPI.update(editId, payload);
        toast.success('Association mise a jour');
      } else {
        await associationsAPI.create(payload);
        toast.success('Association creee');
      }
      setShowForm(false);
      setForm({ ...emptyForm });
      setEditId(null);
      load();
    } catch {
      toast.error('Erreur lors de l\'enregistrement');
    }
  };

  const cancelForm = () => {
    setShowForm(false);
    setForm({ ...emptyForm });
    setEditId(null);
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Associations / Familles d'accueil</h1>
          <span className="page-subtitle">{associations.length} association(s)</span>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => { cancelForm(); setShowForm(true); }}>+ Nouvelle association</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>
            {editId ? 'Modifier l\'association' : 'Nouvelle association'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Nom *</label>
                <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Personne de contact</label>
                <input className="form-input" value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Email</label>
                <input type="email" className="form-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Telephone</label>
                <input className="form-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Remise (%)</label>
                <input type="number" className="form-input" value={form.discount_percent} onChange={(e) => setForm({ ...form, discount_percent: e.target.value })} min="0" max="100" step="0.1" />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Adresse</label>
              <input className="form-input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Notes</label>
              <textarea className="form-textarea" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">{editId ? 'Mettre a jour' : 'Enregistrer'}</button>
              <button type="button" className="btn btn-secondary" onClick={cancelForm}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>Contact</th>
                <th>Email</th>
                <th>Telephone</th>
                <th>Remise</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {associations.map((a) => (
                <tr key={a.id}>
                  <td style={{ fontWeight: 500 }}>{a.name}</td>
                  <td>{a.contact_name || '-'}</td>
                  <td>{a.email || '-'}</td>
                  <td>{a.phone || '-'}</td>
                  <td>{a.discount_percent != null ? `${a.discount_percent}%` : '-'}</td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(a)}>Modifier</button>
                  </td>
                </tr>
              ))}
              {associations.length === 0 && (
                <tr><td colSpan="6" className="table-empty">Aucune association enregistree</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
