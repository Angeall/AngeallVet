import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { medicalAPI } from '../services/api';
import toast from 'react-hot-toast';

const typeLabels = {
  consultation: 'Consultation', vaccination: 'Vaccination', surgery: 'Chirurgie',
  lab_result: 'Labo', imaging: 'Imagerie', note: 'Note',
};

export default function MedicalRecordsPage() {
  const [records, setRecords] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [tab, setTab] = useState('records');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    animal_id: '', record_type: 'consultation',
    subjective: '', objective: '', assessment: '', plan: '', notes: '',
  });

  // Template creation state
  const [showTemplateForm, setShowTemplateForm] = useState(false);
  const [templateForm, setTemplateForm] = useState({
    name: '', category: '', species: '',
    subjective: '', objective: '', assessment: '', plan: '',
  });

  const load = async () => {
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
  };

  useEffect(() => { load(); }, []);

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
      toast.success('Dossier medical cree');
      setShowForm(false);
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  const handleTemplateSubmit = async (e) => {
    e.preventDefault();
    try {
      await medicalAPI.createTemplate({
        ...templateForm,
        category: templateForm.category || null,
        species: templateForm.species || null,
      });
      toast.success('Template cree');
      setShowTemplateForm(false);
      setTemplateForm({ name: '', category: '', species: '', subjective: '', objective: '', assessment: '', plan: '' });
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Dossiers medicaux</h1>
        </div>
        <div className="page-header-actions">
          {tab === 'records' && (
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouveau dossier</button>
          )}
          {tab === 'templates' && (
            <button className="btn btn-primary" onClick={() => setShowTemplateForm(!showTemplateForm)}>+ Nouveau template</button>
          )}
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'records' ? 'tab active' : 'tab'} onClick={() => setTab('records')}>Dossiers</button>
        <button className={tab === 'templates' ? 'tab active' : 'tab'} onClick={() => setTab('templates')}>Templates</button>
      </div>

      {tab === 'records' && (
        <>
          {showForm && (
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau dossier medical (SOAP)</h3>
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
                      <option value="">-- Choisir un modele --</option>
                      {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">S - Subjectif (Motif / Anamnese)</label>
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
            <table>
              <thead>
                <tr><th>Date</th><th>Type</th><th>Animal ID</th><th>Motif</th><th>Diagnostic</th></tr>
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
                    <td><Link to={`/animals/${r.animal_id}`} className="table-link">#{r.animal_id}</Link></td>
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
        </>
      )}

      {tab === 'templates' && (
        <>
          {showTemplateForm && (
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau template de consultation</h3>
              <form onSubmit={handleTemplateSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Nom du template *</label>
                    <input className="form-input" value={templateForm.name} onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })} required placeholder="Ex: Consultation dermatologie" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Categorie</label>
                    <input className="form-input" value={templateForm.category} onChange={(e) => setTemplateForm({ ...templateForm, category: e.target.value })} placeholder="Ex: Dermatologie, Cardiologie..." />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Espece</label>
                    <select className="form-select" value={templateForm.species} onChange={(e) => setTemplateForm({ ...templateForm, species: e.target.value })}>
                      <option value="">-- Toutes --</option>
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
                <div className="form-group">
                  <label className="form-label">S - Subjectif (pre-remplissage)</label>
                  <textarea className="form-textarea" value={templateForm.subjective} onChange={(e) => setTemplateForm({ ...templateForm, subjective: e.target.value })} placeholder="Texte par defaut pour le motif / anamnese" />
                </div>
                <div className="form-group">
                  <label className="form-label">O - Objectif (pre-remplissage)</label>
                  <textarea className="form-textarea" value={templateForm.objective} onChange={(e) => setTemplateForm({ ...templateForm, objective: e.target.value })} placeholder="Texte par defaut pour l'examen clinique" />
                </div>
                <div className="form-group">
                  <label className="form-label">A - Assessment (pre-remplissage)</label>
                  <textarea className="form-textarea" value={templateForm.assessment} onChange={(e) => setTemplateForm({ ...templateForm, assessment: e.target.value })} placeholder="Texte par defaut pour le diagnostic" />
                </div>
                <div className="form-group">
                  <label className="form-label">P - Plan (pre-remplissage)</label>
                  <textarea className="form-textarea" value={templateForm.plan} onChange={(e) => setTemplateForm({ ...templateForm, plan: e.target.value })} placeholder="Texte par defaut pour le plan de traitement" />
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Creer le template</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowTemplateForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <div className="card">
            <table>
              <thead>
                <tr><th>Nom</th><th>Categorie</th><th>Espece</th><th>Cree le</th></tr>
              </thead>
              <tbody>
                {templates.map((t) => (
                  <tr key={t.id}>
                    <td><strong>{t.name}</strong></td>
                    <td>{t.category || '-'}</td>
                    <td>{t.species || 'Toutes'}</td>
                    <td>{new Date(t.created_at).toLocaleDateString('fr-FR')}</td>
                  </tr>
                ))}
                {templates.length === 0 && (
                  <tr><td colSpan="4" className="table-empty">Aucun template</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
