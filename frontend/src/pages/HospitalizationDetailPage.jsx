import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { hospitalizationAPI } from '../services/api';
import toast from 'react-hot-toast';

const taskTypeLabels = { medication: 'Medicament', vitals: 'Constantes', feeding: 'Alimentation', observation: 'Observation' };

export default function HospitalizationDetailPage() {
  const { id } = useParams();
  const [hosp, setHosp] = useState(null);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [showQuickLog, setShowQuickLog] = useState(false);
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [taskForm, setTaskForm] = useState({ scheduled_at: '', task_type: 'medication', description: '' });
  const [quickLogForm, setQuickLogForm] = useState({ task_type: 'medication', description: '', notes: '' });
  const [noteText, setNoteText] = useState('');

  const load = async () => {
    try {
      const res = await hospitalizationAPI.get(id);
      setHosp(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, [id]);

  const completeTask = async (taskId) => {
    try {
      await hospitalizationAPI.updateTask(id, taskId, { is_completed: true });
      toast.success('Tache completee');
      load();
    } catch { toast.error('Erreur'); }
  };

  const cancelTask = async (taskId) => {
    try {
      await hospitalizationAPI.updateTask(id, taskId, { notes: 'Annule' });
      toast.success('Note ajoutee');
      load();
    } catch { toast.error('Erreur'); }
  };

  const addTask = async (e) => {
    e.preventDefault();
    try {
      await hospitalizationAPI.addTask(id, taskForm);
      toast.success('Tache ajoutee');
      setShowTaskForm(false);
      setTaskForm({ scheduled_at: '', task_type: 'medication', description: '' });
      load();
    } catch { toast.error('Erreur'); }
  };

  const addQuickLog = async (e) => {
    e.preventDefault();
    try {
      await hospitalizationAPI.addTask(id, {
        scheduled_at: new Date().toISOString(),
        task_type: quickLogForm.task_type,
        description: quickLogForm.description,
        is_completed: true,
      });
      toast.success('Soin enregistre dans l\'historique');
      setShowQuickLog(false);
      setQuickLogForm({ task_type: 'medication', description: '', notes: '' });
      load();
    } catch { toast.error('Erreur'); }
  };

  const addNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    try {
      const currentNotes = hosp.notes ? hosp.notes + '\n' : '';
      const timestamp = new Date().toLocaleString('fr-FR');
      await hospitalizationAPI.update(id, { notes: currentNotes + `[${timestamp}] ${noteText}` });
      toast.success('Remarque ajoutee');
      setNoteText('');
      setShowNoteForm(false);
      load();
    } catch { toast.error('Erreur'); }
  };

  const discharge = async () => {
    try {
      await hospitalizationAPI.update(id, { status: 'discharged' });
      toast.success('Animal sorti');
      load();
    } catch { toast.error('Erreur'); }
  };

  if (!hosp) return <div className="page-content">Chargement...</div>;

  const completedTasks = (hosp.care_tasks || []).filter(t => t.is_completed);
  const pendingTasks = (hosp.care_tasks || []).filter(t => !t.is_completed);

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <nav className="page-breadcrumb">
            <Link to="/hospitalization">Hospitalisation</Link>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{hosp.animal_name || `Animal #${hosp.animal_id}`}</span>
          </nav>
          <h1 className="page-title">
            <Link to={`/animals/${hosp.animal_id}`} className="table-link">{hosp.animal_name || `Animal #${hosp.animal_id}`}</Link>
            {' '}- Cage {hosp.cage_number || 'N/A'}
          </h1>
          {hosp.client_name && <span style={{ fontSize: '0.9rem', color: 'var(--gray-500)', marginLeft: '12px' }}>{hosp.client_name}</span>}
          {hosp.veterinarian_name && <span style={{ fontSize: '0.9rem', color: 'var(--gray-500)', marginLeft: '12px' }}>{hosp.veterinarian_name}</span>}
        </div>
        <div className="page-header-actions">
          <span className={`badge badge-${hosp.status === 'active' ? 'green' : 'gray'}`} style={{ marginRight: '8px' }}>{hosp.status}</span>
          {hosp.status === 'active' && (
            <button className="btn btn-secondary" onClick={discharge}>Sortie d'hospitalisation</button>
          )}
        </div>
      </div>

      <div className="card">
        <div className="form-row">
          <div><strong>Motif:</strong> {hosp.reason}</div>
          <div><strong>Admis le:</strong> {new Date(hosp.admitted_at).toLocaleString('fr-FR')}</div>
          {hosp.discharged_at && <div><strong>Sorti le:</strong> {new Date(hosp.discharged_at).toLocaleString('fr-FR')}</div>}
        </div>
      </div>

      {/* Pending tasks */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">A faire ({pendingTasks.length})</h3>
          {hosp.status === 'active' && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowTaskForm(!showTaskForm)}>+ Ajouter une tache</button>
          )}
        </div>

        {showTaskForm && (
          <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <form onSubmit={addTask}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Date/heure *</label>
                  <input type="datetime-local" className="form-input" value={taskForm.scheduled_at} onChange={(e) => setTaskForm({ ...taskForm, scheduled_at: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Type *</label>
                  <select className="form-select" value={taskForm.task_type} onChange={(e) => setTaskForm({ ...taskForm, task_type: e.target.value })}>
                    {Object.entries(taskTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Description *</label>
                <input className="form-input" value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} required />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" className="btn btn-primary">Ajouter</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowTaskForm(false)}>Annuler</button>
              </div>
            </form>
          </div>
        )}

        {pendingTasks.length > 0 ? (
          <table>
            <thead><tr><th>Date/Heure</th><th>Type</th><th>Description</th><th>Actions</th></tr></thead>
            <tbody>
              {pendingTasks.sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at)).map((task) => (
                <tr key={task.id}>
                  <td>{new Date(task.scheduled_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</td>
                  <td><span className="badge badge-blue">{taskTypeLabels[task.task_type] || task.task_type}</span></td>
                  <td>{task.description}</td>
                  <td style={{ display: 'flex', gap: '4px' }}>
                    <button className="btn btn-success btn-sm" onClick={() => completeTask(task.id)}>Fait</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => cancelTask(task.id)}>Annuler</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucune tache en attente</p>
        )}
      </div>

      {/* Completed tasks / History */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Historique des soins ({completedTasks.length})</h3>
          {hosp.status === 'active' && (
            <button className="btn btn-success btn-sm" onClick={() => setShowQuickLog(!showQuickLog)}>+ Enregistrer un soin realise</button>
          )}
        </div>

        {showQuickLog && (
          <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <form onSubmit={addQuickLog}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Type *</label>
                  <select className="form-select" value={quickLogForm.task_type} onChange={(e) => setQuickLogForm({ ...quickLogForm, task_type: e.target.value })}>
                    {Object.entries(taskTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ flex: 2 }}>
                  <label className="form-label">Description *</label>
                  <input className="form-input" value={quickLogForm.description} onChange={(e) => setQuickLogForm({ ...quickLogForm, description: e.target.value })} placeholder="Ex: Injection Metacam 0.5ml, prise de constantes..." required />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" className="btn btn-success">Enregistrer dans l'historique</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowQuickLog(false)}>Annuler</button>
              </div>
            </form>
          </div>
        )}

        {completedTasks.length > 0 ? (
          <table>
            <thead><tr><th>Prevu</th><th>Realise</th><th>Type</th><th>Description</th><th>Notes</th></tr></thead>
            <tbody>
              {completedTasks.sort((a, b) => new Date(b.completed_at || b.scheduled_at) - new Date(a.completed_at || a.scheduled_at)).map((task) => (
                <tr key={task.id} style={{ opacity: 0.8 }}>
                  <td>{new Date(task.scheduled_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</td>
                  <td>{task.completed_at ? new Date(task.completed_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}</td>
                  <td><span className="badge badge-green">{taskTypeLabels[task.task_type] || task.task_type}</span></td>
                  <td>{task.description}</td>
                  <td>{task.notes || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun soin realise</p>
        )}
      </div>

      {/* Remarks / Notes timeline */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Remarques</h3>
          <button className="btn btn-primary btn-sm" onClick={() => setShowNoteForm(!showNoteForm)}>+ Ajouter</button>
        </div>

        {showNoteForm && (
          <form onSubmit={addNote} style={{ marginBottom: '16px' }}>
            <div className="form-group">
              <textarea className="form-textarea" value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Remarque, observation..." required />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary btn-sm">Ajouter</button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowNoteForm(false)}>Annuler</button>
            </div>
          </form>
        )}

        {hosp.notes ? (
          <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: '1.6' }}>{hosp.notes}</div>
        ) : (
          <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucune remarque</p>
        )}
      </div>
    </div>
  );
}
