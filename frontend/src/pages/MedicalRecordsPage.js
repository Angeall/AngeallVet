import React, { useState, useEffect } from 'react';
import { medicalAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function MedicalRecordsPage() {
  const [records, setRecords] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    animal_id: '', record_type: 'consultation',
    subjective: '', objective: '', assessment: '', plan: '', notes: '',
  });

  useEffect(() => {
    async function load() {
      try {
        const [rRes, tRes] = await Promise.all([
          medicalAPI.listRecords({}),
          medicalAPI.listTemplates({}),
        ]);
        setRecords(rRes.data);
        setTemplates(tRes.data);
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, []);

  const applyTemplate = (templateId) => {
    const t = templates.find((tp) => tp.id === parseInt(templateId));
    if (t) {
      setForm({
        ...form,
        subjective: t.subjective || '',
        objective: t.objective || '',
        assessment: t.assessment || '',
        plan: t.plan || '',
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await medicalAPI.createRecord({
        ...form,
        animal_id: parseInt(form.animal_id),
      });
      toast.success('Dossier médical créé');
      setShowForm(false);
      const res = await medicalAPI.listRecords({});
      setRecords(res.data);
    } catch {
      toast.error('Erreur lors de la création');
    }
  };

  const typeLabels = {
    consultation: 'Consultation', vaccination: 'Vaccination', surgery: 'Chirurgie',
    lab_result: 'Labo', imaging: 'Imagerie', note: 'Note',
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Dossiers médicaux</h1>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            + Nouveau dossier
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau dossier médical (SOAP)</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">ID Animal *</label>
                <input className="form-input" value={form.animal_id} onChange={(e) => setForm({ ...form, animal_id: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Type *</label>
                <select className="form-select" value={form.record_type} onChange={(e) => setForm({ ...form, record_type: e.target.value })}>
                  {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Template</label>
                <select className="form-select" onChange={(e) => applyTemplate(e.target.value)}>
                  <option value="">-- Choisir un modèle --</option>
                  {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">S - Subjectif (Motif / Anamnèse)</label>
              <textarea className="form-textarea" value={form.subjective} onChange={(e) => setForm({ ...form, subjective: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">O - Objectif (Examen clinique)</label>
              <textarea className="form-textarea" value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">A - Assessment (Diagnostic)</label>
              <textarea className="form-textarea" value={form.assessment} onChange={(e) => setForm({ ...form, assessment: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">P - Plan (Traitement)</label>
              <textarea className="form-textarea" value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Animal ID</th>
                <th>Motif</th>
                <th>Diagnostic</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.created_at).toLocaleDateString('fr-FR')}</td>
                  <td>
                    <span className={`badge badge-${r.record_type === 'vaccination' ? 'green' : r.record_type === 'surgery' ? 'red' : 'blue'}`}>
                      {typeLabels[r.record_type] || r.record_type}
                    </span>
                  </td>
                  <td>{r.animal_id}</td>
                  <td>{r.subjective ? r.subjective.substring(0, 80) + (r.subjective.length > 80 ? '...' : '') : '-'}</td>
                  <td>{r.assessment ? r.assessment.substring(0, 80) + (r.assessment.length > 80 ? '...' : '') : '-'}</td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr><td colSpan="5" className="table-empty">Aucun dossier</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
