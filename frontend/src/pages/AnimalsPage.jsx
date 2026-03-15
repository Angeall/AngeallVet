import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { animalsAPI, clientsAPI, associationsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function AnimalsPage() {
  const [animals, setAnimals] = useState([]);
  const [search, setSearch] = useState('');
  const [speciesFilter, setSpeciesFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    client_id: '', name: '', species: 'dog', breed: '', sex: 'male',
    date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false,
    association_id: '',
  });

  // Associations
  const [associationsList, setAssociationsList] = useState([]);

  // Client search state
  const [clientSearch, setClientSearch] = useState('');
  const [clientResults, setClientResults] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);

  // Quick client creation modal
  const [showClientModal, setShowClientModal] = useState(false);
  const [clientForm, setClientForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });

  const load = useCallback(async () => {
    try {
      const res = await animalsAPI.list({
        search: search || undefined,
        species: speciesFilter || undefined,
      });
      setAnimals(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  }, [search, speciesFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    associationsAPI.list().then(res => setAssociationsList(res.data || [])).catch(() => {});
  }, []);

  // Client search with debounce
  useEffect(() => {
    if (clientSearch.length < 2) { setClientResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await clientsAPI.list({ search: clientSearch });
        setClientResults(res.data || []);
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [clientSearch]);

  const selectClient = (client) => {
    setSelectedClient(client);
    setForm(prev => ({ ...prev, client_id: client.id }));
    setClientSearch(`${client.last_name} ${client.first_name}`);
    setClientResults([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await animalsAPI.create({
        ...form,
        client_id: parseInt(form.client_id),
        date_of_birth: form.date_of_birth || null,
        microchip_number: form.microchip_number || null,
        tattoo_number: form.tattoo_number || null,
        association_id: form.association_id ? parseInt(form.association_id) : null,
      });
      toast.success('Animal cree');
      setShowForm(false);
      setForm({ client_id: '', name: '', species: 'dog', breed: '', sex: 'male', date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false, association_id: '' });
      setSelectedClient(null);
      setClientSearch('');
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  const handleCreateClient = async (e) => {
    e.preventDefault();
    try {
      const payload = Object.fromEntries(
        Object.entries(clientForm).map(([k, v]) => [k, v === '' ? null : v])
      );
      const res = await clientsAPI.create(payload);
      toast.success('Client cree');
      setShowClientModal(false);
      setClientForm({ first_name: '', last_name: '', phone: '', email: '' });
      selectClient(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors de la creation du client');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Animaux</h1>
          <span className="page-subtitle">{animals.length} animal(aux) enregistre(s)</span>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouvel animal</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouvel animal</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group" style={{ position: 'relative' }}>
                <label className="form-label">Client *</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    className="form-input"
                    placeholder="Rechercher un client..."
                    value={clientSearch}
                    onChange={(e) => { setClientSearch(e.target.value); setSelectedClient(null); setForm(prev => ({ ...prev, client_id: '' })); }}
                    required={!selectedClient}
                    style={{ flex: 1 }}
                  />
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowClientModal(true)} title="Creer un nouveau client">+ Client</button>
                </div>
                {clientResults.length > 0 && !selectedClient && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                    {clientResults.map(c => (
                      <div key={c.id} onClick={() => selectClient(c)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                        onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                        onMouseLeave={(e) => e.target.style.background = 'white'}>
                        <strong>{c.last_name} {c.first_name}</strong>
                        <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{c.phone || c.email || ''}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="form-group">
                <label className="form-label">Nom *</label>
                <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Espece *</label>
                <select className="form-select" value={form.species} onChange={(e) => setForm({ ...form, species: e.target.value })}>
                  <option value="dog">Chien</option>
                  <option value="cat">Chat</option>
                  <option value="bird">Oiseau</option>
                  <option value="rabbit">Lapin</option>
                  <option value="reptile">Reptile</option>
                  <option value="horse">Cheval</option>
                  <option value="nac">NAC</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Race</label>
                <input className="form-input" value={form.breed} onChange={(e) => setForm({ ...form, breed: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Sexe</label>
                <select className="form-select" value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
                  <option value="male">Male</option>
                  <option value="female">Femelle</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Date de naissance</label>
                <input type="date" className="form-input" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Couleur</label>
                <input className="form-input" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">N Puce</label>
                <input className="form-input" value={form.microchip_number} onChange={(e) => setForm({ ...form, microchip_number: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">N Tatouage</label>
                <input className="form-input" value={form.tattoo_number} onChange={(e) => setForm({ ...form, tattoo_number: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input type="checkbox" checked={form.is_neutered} onChange={(e) => setForm({ ...form, is_neutered: e.target.checked })} />
                  Sterilise
                </label>
              </div>
              {associationsList.length > 0 && (
                <div className="form-group">
                  <label className="form-label">Association / Famille d'accueil</label>
                  <select className="form-select" value={form.association_id} onChange={(e) => setForm({ ...form, association_id: e.target.value })}>
                    <option value="">-- Aucune --</option>
                    {associationsList.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      {/* Quick client creation modal */}
      {showClientModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={(e) => { if (e.target === e.currentTarget) setShowClientModal(false); }}>
          <div className="card" style={{ width: '480px', maxWidth: '90vw', margin: 0 }}>
            <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau client</h3>
            <form onSubmit={handleCreateClient}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Prenom *</label>
                  <input className="form-input" value={clientForm.first_name} onChange={(e) => setClientForm({ ...clientForm, first_name: e.target.value })} required autoFocus />
                </div>
                <div className="form-group">
                  <label className="form-label">Nom *</label>
                  <input className="form-input" value={clientForm.last_name} onChange={(e) => setClientForm({ ...clientForm, last_name: e.target.value })} required />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Telephone</label>
                  <input className="form-input" value={clientForm.phone} onChange={(e) => setClientForm({ ...clientForm, phone: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input type="email" className="form-input" value={clientForm.email} onChange={(e) => setClientForm({ ...clientForm, email: e.target.value })} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowClientModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary">Creer et selectionner</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="form-row" style={{ marginBottom: '16px' }}>
          <div className="search-input-wrapper">
            <input className="form-input" placeholder="Rechercher par nom, puce, tatouage..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="form-select" value={speciesFilter} onChange={(e) => setSpeciesFilter(e.target.value)}>
            <option value="">Toutes especes</option>
            <option value="dog">Chien</option>
            <option value="cat">Chat</option>
            <option value="bird">Oiseau</option>
            <option value="rabbit">Lapin</option>
            <option value="reptile">Reptile</option>
            <option value="horse">Cheval</option>
            <option value="nac">NAC</option>
          </select>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Nom</th><th>Espece</th><th>Race</th><th>Sexe</th><th>Sterilise</th><th>N Puce</th><th>Association</th><th>Alertes</th>
              </tr>
            </thead>
            <tbody>
              {animals.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={`/animals/${a.id}`} className="table-link">{a.name}</Link>
                    {a.is_deceased && <span className="badge badge-gray" style={{ marginLeft: '8px' }}>Decede</span>}
                  </td>
                  <td>{a.species}</td>
                  <td>{a.breed || '-'}</td>
                  <td>{a.sex === 'male' ? 'M' : a.sex === 'female' ? 'F' : '?'}</td>
                  <td>{a.is_neutered ? 'Oui' : 'Non'}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{a.microchip_number || '-'}</td>
                  <td>{a.association_name ? <span className="badge badge-purple">{a.association_name}</span> : '-'}</td>
                  <td>
                    {a.alerts?.filter((al) => al.is_active).map((al) => (
                      <span key={al.id} className={`badge badge-${al.severity === 'danger' ? 'red' : al.severity === 'warning' ? 'amber' : 'blue'}`} style={{ marginRight: '4px' }}>
                        {al.alert_type}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
              {animals.length === 0 && (
                <tr><td colSpan="8" className="table-empty">Aucun animal trouve</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
