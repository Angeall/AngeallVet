import React, { useState, useEffect } from 'react';
import { hospitalizationAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function HospitalizationPage() {
  const [hospitalizations, setHospitalizations] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ animal_id: '', reason: '', cage_number: '' });

  const load = async () => {
    try {
      const res = await hospitalizationAPI.list({});
      setHospitalizations(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await hospitalizationAPI.create({
        animal_id: parseInt(form.animal_id),
        reason: form.reason,
        cage_number: form.cage_number || null,
      });
      toast.success('Hospitalisation créée');
      setShowForm(false);
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const discharge = async (id) => {
    try {
      await hospitalizationAPI.update(id, { status: 'discharged' });
      toast.success('Animal sorti');
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const completeTask = async (hospId, taskId) => {
    try {
      await hospitalizationAPI.updateTask(hospId, taskId, { is_completed: true });
      toast.success('Tâche complétée');
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Hospitalisation</h1>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouvelle hospitalisation</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">ID Animal *</label>
                <input className="form-input" value={form.animal_id} onChange={(e) => setForm({ ...form, animal_id: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Cage</label>
                <input className="form-input" value={form.cage_number} onChange={(e) => setForm({ ...form, cage_number: e.target.value })} />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Motif *</label>
              <textarea className="form-textarea" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} required />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Hospitaliser</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      {hospitalizations.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏥</div>
          <h3>Aucune hospitalisation active</h3>
          <p>Les animaux hospitalisés apparaîtront ici</p>
        </div>
      ) : (
        hospitalizations.map((h) => (
          <div key={h.id} className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Animal #{h.animal_id} - Cage {h.cage_number || 'N/A'}</h3>
                <span className={`badge badge-${h.status === 'active' ? 'green' : 'gray'}`}>{h.status}</span>
              </div>
              {h.status === 'active' && (
                <button className="btn btn-secondary btn-sm" onClick={() => discharge(h.id)}>Sortie</button>
              )}
            </div>
            <p><strong>Motif:</strong> {h.reason}</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
              Admis le {new Date(h.admitted_at).toLocaleString('fr-FR')}
            </p>

            {h.care_tasks && h.care_tasks.length > 0 && (
              <div className="care-sheet">
                <h4 className="care-sheet-title">Feuille de soins</h4>
                <table>
                  <thead><tr><th>Heure</th><th>Type</th><th>Description</th><th>Statut</th><th></th></tr></thead>
                  <tbody>
                    {h.care_tasks.map((task) => (
                      <tr key={task.id} className={`care-task ${task.is_completed ? 'completed' : ''}`}>
                        <td>{new Date(task.scheduled_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td>
                        <td><span className="badge badge-blue">{task.task_type}</span></td>
                        <td>{task.description}</td>
                        <td>
                          {task.is_completed
                            ? <span className="badge badge-green">Fait</span>
                            : <span className="badge badge-amber">En attente</span>
                          }
                        </td>
                        <td>
                          {!task.is_completed && (
                            <button className="btn btn-success btn-sm" onClick={() => completeTask(h.id, task.id)}>Valider</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
