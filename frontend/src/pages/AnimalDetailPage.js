import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { animalsAPI, medicalAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

export default function AnimalDetailPage() {
  const { id } = useParams();
  const [animal, setAnimal] = useState(null);
  const [weights, setWeights] = useState([]);
  const [records, setRecords] = useState([]);
  const [tab, setTab] = useState('info');
  const [newWeight, setNewWeight] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [aRes, wRes, rRes] = await Promise.all([
          animalsAPI.get(id),
          animalsAPI.getWeights(id),
          medicalAPI.listRecords({ animal_id: id }),
        ]);
        setAnimal(aRes.data);
        setWeights(wRes.data);
        setRecords(rRes.data);
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, [id]);

  const addWeight = async (e) => {
    e.preventDefault();
    if (!newWeight) return;
    try {
      await animalsAPI.addWeight(id, { weight_kg: parseFloat(newWeight) });
      const wRes = await animalsAPI.getWeights(id);
      setWeights(wRes.data);
      setNewWeight('');
      toast.success('Poids enregistré');
    } catch {
      toast.error('Erreur');
    }
  };

  if (!animal) return <div className="page-content">Chargement...</div>;

  const weightChartData = [...weights].reverse().map((w) => ({
    date: new Date(w.recorded_at).toLocaleDateString('fr-FR'),
    poids: parseFloat(w.weight_kg),
  }));

  const recordTypeLabel = {
    consultation: 'Consultation',
    vaccination: 'Vaccination',
    surgery: 'Chirurgie',
    lab_result: 'Labo',
    imaging: 'Imagerie',
    note: 'Note',
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/animals" className="breadcrumb-link">
            Animaux /
          </Link>
          <h1 className="page-title">
            {animal.name}
          </h1>
        </div>
      </div>

      {/* Alerts */}
      {animal.alerts?.filter((a) => a.is_active).map((alert) => (
        <div key={alert.id} className={`alert-banner ${alert.severity}`}>
          {alert.severity === 'danger' ? '⚠️' : alert.severity === 'warning' ? '⚡' : 'ℹ️'}
          <strong>{alert.alert_type}:</strong> {alert.message}
        </div>
      ))}

      {/* Info card */}
      <div className="card">
        <div className="form-row">
          <div><strong>Espèce:</strong> {animal.species}</div>
          <div><strong>Race:</strong> {animal.breed || '-'}</div>
          <div><strong>Sexe:</strong> {animal.sex}</div>
          <div><strong>Né(e) le:</strong> {animal.date_of_birth || '-'}</div>
          <div><strong>Couleur:</strong> {animal.color || '-'}</div>
          <div><strong>Stérilisé:</strong> {animal.is_neutered ? 'Oui' : 'Non'}</div>
          <div><strong>Puce:</strong> {animal.microchip_number || '-'}</div>
          <div><strong>Tatouage:</strong> {animal.tattoo_number || '-'}</div>
        </div>
      </div>

      <div className="tabs">
        {['info', 'weight', 'medical'].map((t) => (
          <button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>
            {t === 'info' ? 'Informations' : t === 'weight' ? 'Courbe de poids' : 'Dossier médical'}
          </button>
        ))}
      </div>

      {tab === 'weight' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Courbe de poids</h3>
            <form onSubmit={addWeight} style={{ display: 'flex', gap: '8px' }}>
              <input
                type="number"
                step="0.01"
                className="form-input"
                style={{ width: '120px' }}
                placeholder="Poids (kg)"
                value={newWeight}
                onChange={(e) => setNewWeight(e.target.value)}
              />
              <button type="submit" className="btn btn-primary btn-sm">Ajouter</button>
            </form>
          </div>
          {weightChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={weightChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis unit=" kg" />
                <Tooltip />
                <Line type="monotone" dataKey="poids" stroke="var(--primary)" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucune donnée de poids</p>
          )}
        </div>
      )}

      {tab === 'medical' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Historique médical</h3>
          </div>
          <div className="timeline">
            {records.map((r) => (
              <div key={r.id} className="timeline-item">
                <div className={`timeline-dot ${r.record_type}`} />
                <div className="card" style={{ marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span className={`badge badge-${r.record_type === 'vaccination' ? 'green' : r.record_type === 'surgery' ? 'red' : 'blue'}`}>
                      {recordTypeLabel[r.record_type] || r.record_type}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>
                      {new Date(r.created_at).toLocaleDateString('fr-FR')}
                    </span>
                  </div>
                  {r.subjective && <p><strong>Motif:</strong> {r.subjective}</p>}
                  {r.assessment && <p><strong>Diagnostic:</strong> {r.assessment}</p>}
                  {r.plan && <p><strong>Plan:</strong> {r.plan}</p>}
                </div>
              </div>
            ))}
            {records.length === 0 && (
              <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun dossier médical</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
