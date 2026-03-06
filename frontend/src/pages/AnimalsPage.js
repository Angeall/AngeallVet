import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { animalsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function AnimalsPage() {
  const [animals, setAnimals] = useState([]);
  const [search, setSearch] = useState('');
  const [speciesFilter, setSpeciesFilter] = useState('');

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

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Animaux</h1>
          <span className="page-subtitle">{animals.length} animal(aux) enregistré(s)</span>
        </div>
      </div>

      <div className="card">
        <div className="form-row" style={{ marginBottom: '16px' }}>
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              className="form-input"
              placeholder="Rechercher par nom, puce, tatouage..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select className="form-select" value={speciesFilter} onChange={(e) => setSpeciesFilter(e.target.value)}>
            <option value="">Toutes espèces</option>
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
                <th>Nom</th>
                <th>Espèce</th>
                <th>Race</th>
                <th>Sexe</th>
                <th>Stérilisé</th>
                <th>N° Puce</th>
                <th>Alertes</th>
              </tr>
            </thead>
            <tbody>
              {animals.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={`/animals/${a.id}`} className="table-link">
                      {a.name}
                    </Link>
                    {a.is_deceased && <span className="badge badge-gray" style={{ marginLeft: '8px' }}>Décédé</span>}
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
                <tr><td colSpan="7" className="table-empty">Aucun animal trouvé</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
