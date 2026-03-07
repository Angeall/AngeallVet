import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { animalsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function AnimalsPage() {
  const [animals, setAnimals] = useState([]);
  const [search, setSearch] = useState('');
  const [speciesFilter, setSpeciesFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    client_id: '', name: '', species: 'dog', breed: '', sex: 'male',
    date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false,
  });

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await animalsAPI.create({
        ...form,
        client_id: parseInt(form.client_id),
        date_of_birth: form.date_of_birth || null,
        microchip_number: form.microchip_number || null,
        tattoo_number: form.tattoo_number || null,
      });
      toast.success('Animal cree');
      setShowForm(false);
      setForm({ client_id: '', name: '', species: 'dog', breed: '', sex: 'male', date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false });
      load();
    } catch {
      toast.error('Erreur lors de la creation');
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
              <div className="form-group">
                <label className="form-label">ID Client *</label>
                <input className="form-input" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} required />
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
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" checked={form.is_neutered} onChange={(e) => setForm({ ...form, is_neutered: e.target.checked })} />
                Sterilise
              </label>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
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
                <th>Nom</th><th>Espece</th><th>Race</th><th>Sexe</th><th>Sterilise</th><th>N Puce</th><th>Alertes</th>
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
                <tr><td colSpan="7" className="table-empty">Aucun animal trouve</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
