import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { animalsAPI, medicalAPI, hospitalizationAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

export default function AnimalDetailPage() {
  const { id } = useParams();
  const [animal, setAnimal] = useState(null);
  const [weights, setWeights] = useState([]);
  const [records, setRecords] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [hospitalizations, setHospitalizations] = useState([]);
  const [tab, setTab] = useState('info');
  const [newWeight, setNewWeight] = useState('');
  const [showRecordForm, setShowRecordForm] = useState(false);
  const [showHospForm, setShowHospForm] = useState(false);
  const [recordForm, setRecordForm] = useState({
    record_type: 'consultation', subjective: '', objective: '', assessment: '', plan: '', notes: '',
  });
  const [hospForm, setHospForm] = useState({ reason: '', cage_number: '' });
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [alertForm, setAlertForm] = useState({ alert_type: 'allergy', message: '', severity: 'warning' });

  const load = async () => {
    try {
      const [aRes, wRes, rRes, tRes, hRes] = await Promise.all([
        animalsAPI.get(id),
        animalsAPI.getWeights(id),
        medicalAPI.listRecords({ animal_id: id }),
        medicalAPI.listTemplates({}),
        hospitalizationAPI.list({ animal_id: id }),
      ]);
      setAnimal(aRes.data);
      setWeights(wRes.data);
      setRecords(rRes.data);
      setTemplates(tRes.data);
      setHospitalizations(hRes.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, [id]);

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

  const applyTemplate = (templateId) => {
    const t = templates.find((tp) => tp.id === parseInt(templateId));
    if (t) {
      setRecordForm({
        ...recordForm,
        subjective: t.subjective || '',
        objective: t.objective || '',
        assessment: t.assessment || '',
        plan: t.plan || '',
      });
    }
  };

  const handleRecordSubmit = async (e) => {
    e.preventDefault();
    try {
      await medicalAPI.createRecord({ ...recordForm, animal_id: parseInt(id) });
      toast.success('Dossier médical créé');
      setShowRecordForm(false);
      setRecordForm({ record_type: 'consultation', subjective: '', objective: '', assessment: '', plan: '', notes: '' });
      const rRes = await medicalAPI.listRecords({ animal_id: id });
      setRecords(rRes.data);
    } catch {
      toast.error('Erreur lors de la création');
    }
  };

  const activeHosp = hospitalizations.find((h) => h.status === 'active');

  const handleHospitalize = async (e) => {
    e.preventDefault();
    try {
      await hospitalizationAPI.create({
        animal_id: parseInt(id),
        reason: hospForm.reason,
        cage_number: hospForm.cage_number || null,
      });
      toast.success('Animal hospitalisé');
      setShowHospForm(false);
      setHospForm({ reason: '', cage_number: '' });
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const handleDischarge = async () => {
    if (!activeHosp) return;
    try {
      await hospitalizationAPI.update(activeHosp.id, { status: 'discharged' });
      toast.success('Animal sorti');
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const handleAlertSubmit = async (e) => {
    e.preventDefault();
    try {
      await animalsAPI.addAlert(id, alertForm);
      toast.success('Alerte ajoutee');
      setShowAlertForm(false);
      setAlertForm({ alert_type: 'allergy', message: '', severity: 'warning' });
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const removeAlert = async (alertId) => {
    try {
      await animalsAPI.removeAlert(id, alertId);
      toast.success('Alerte supprimee');
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  if (!animal) return <div className="page-content">Chargement...</div>;

  const alertTypeLabels = {
    allergy: 'Allergie', aggressive: 'Agressif', chronic: 'Maladie chronique',
    medication: 'Medicament', other: 'Autre',
  };
  const severityLabels = { danger: 'Danger', warning: 'Attention', info: 'Information' };

  const weightChartData = [...weights].reverse().map((w) => ({
    date: new Date(w.recorded_at).toLocaleDateString('fr-FR'),
    poids: parseFloat(w.weight_kg),
  }));

  const recordTypeLabel = {
    consultation: 'Consultation', vaccination: 'Vaccination', surgery: 'Chirurgie',
    lab_result: 'Labo', imaging: 'Imagerie', note: 'Note',
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/animals" className="breadcrumb-link">Animaux /</Link>
          <h1 className="page-title">{animal.name}</h1>
        </div>
        <div className="page-header-actions">
          {activeHosp ? (
            <button className="btn btn-secondary" onClick={handleDischarge}>
              Sortie d'hospitalisation
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => setShowHospForm(!showHospForm)}>
              Hospitaliser
            </button>
          )}
        </div>
      </div>

      {activeHosp && (
        <div className="alert-banner warning">
          Actuellement hospitalisé - Cage {activeHosp.cage_number || 'N/A'} - {activeHosp.reason}
        </div>
      )}

      {showHospForm && !activeHosp && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Hospitaliser {animal.name}</h3>
          <form onSubmit={handleHospitalize}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Motif *</label>
                <textarea className="form-textarea" value={hospForm.reason} onChange={(e) => setHospForm({ ...hospForm, reason: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Cage</label>
                <input className="form-input" value={hospForm.cage_number} onChange={(e) => setHospForm({ ...hospForm, cage_number: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Hospitaliser</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowHospForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      {/* Alerts */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Alertes</h3>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAlertForm(!showAlertForm)}>+ Ajouter une alerte</button>
        </div>

        {showAlertForm && (
          <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <form onSubmit={handleAlertSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Type *</label>
                  <select className="form-select" value={alertForm.alert_type} onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}>
                    {Object.entries(alertTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Severite</label>
                  <select className="form-select" value={alertForm.severity} onChange={(e) => setAlertForm({ ...alertForm, severity: e.target.value })}>
                    {Object.entries(severityLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Message *</label>
                <input className="form-input" value={alertForm.message} onChange={(e) => setAlertForm({ ...alertForm, message: e.target.value })} placeholder="Ex: Allergique a la penicilline" required />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" className="btn btn-primary">Ajouter</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAlertForm(false)}>Annuler</button>
              </div>
            </form>
          </div>
        )}

        {animal.alerts?.filter((a) => a.is_active).length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {animal.alerts.filter((a) => a.is_active).map((alert) => (
              <div key={alert.id} className={`alert-banner ${alert.severity}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: 0 }}>
                <span>
                  {alert.severity === 'danger' ? '!!!' : alert.severity === 'warning' ? '!' : 'i'}
                  {' '}<strong>{alertTypeLabels[alert.alert_type] || alert.alert_type}:</strong> {alert.message}
                </span>
                <button
                  className="btn btn-sm"
                  onClick={() => removeAlert(alert.id)}
                  style={{ background: 'rgba(255,255,255,0.3)', border: 'none', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px' }}
                  title="Supprimer cette alerte"
                >
                  X
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--gray-400)', textAlign: 'center', margin: '8px 0' }}>Aucune alerte active</p>
        )}
      </div>

      {/* Info card */}
      <div className="card">
        <div className="form-row">
          <div><strong>Espece:</strong> {animal.species}</div>
          <div><strong>Race:</strong> {animal.breed || '-'}</div>
          <div><strong>Sexe:</strong> {animal.sex}</div>
          <div><strong>Ne(e) le:</strong> {animal.date_of_birth || '-'}</div>
          <div><strong>Couleur:</strong> {animal.color || '-'}</div>
          <div><strong>Sterilise:</strong> {animal.is_neutered ? 'Oui' : 'Non'}</div>
          <div><strong>Puce:</strong> {animal.microchip_number || '-'}</div>
          <div><strong>Tatouage:</strong> {animal.tattoo_number || '-'}</div>
        </div>
      </div>

      <div className="tabs">
        {['info', 'weight', 'medical'].map((t) => (
          <button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>
            {t === 'info' ? 'Informations' : t === 'weight' ? 'Courbe de poids' : 'Dossier medical'}
          </button>
        ))}
      </div>

      {tab === 'weight' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Courbe de poids</h3>
            <form onSubmit={addWeight} style={{ display: 'flex', gap: '8px' }}>
              <input type="number" step="0.01" className="form-input" style={{ width: '120px' }} placeholder="Poids (kg)" value={newWeight} onChange={(e) => setNewWeight(e.target.value)} />
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
            <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucune donnee de poids</p>
          )}
        </div>
      )}

      {tab === 'medical' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Historique medical</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowRecordForm(!showRecordForm)}>
              + Nouveau dossier
            </button>
          </div>

          {showRecordForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <h4 style={{ marginBottom: '12px' }}>Nouveau dossier medical (SOAP)</h4>
              <form onSubmit={handleRecordSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Type *</label>
                    <select className="form-select" value={recordForm.record_type} onChange={(e) => setRecordForm({ ...recordForm, record_type: e.target.value })}>
                      {Object.entries(recordTypeLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Template</label>
                    <select className="form-select" onChange={(e) => applyTemplate(e.target.value)}>
                      <option value="">-- Choisir un modele --</option>
                      {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">S - Subjectif (Motif / Anamnese)</label>
                  <textarea className="form-textarea" value={recordForm.subjective} onChange={(e) => setRecordForm({ ...recordForm, subjective: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">O - Objectif (Examen clinique)</label>
                  <textarea className="form-textarea" value={recordForm.objective} onChange={(e) => setRecordForm({ ...recordForm, objective: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">A - Assessment (Diagnostic)</label>
                  <textarea className="form-textarea" value={recordForm.assessment} onChange={(e) => setRecordForm({ ...recordForm, assessment: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">P - Plan (Traitement)</label>
                  <textarea className="form-textarea" value={recordForm.plan} onChange={(e) => setRecordForm({ ...recordForm, plan: e.target.value })} />
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Enregistrer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowRecordForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

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
              <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun dossier medical</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
