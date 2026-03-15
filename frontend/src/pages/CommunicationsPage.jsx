import React, { useState, useEffect } from 'react';
import { communicationsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function CommunicationsPage() {
  const [comms, setComms] = useState([]);
  const [rules, setRules] = useState([]);
  const [tab, setTab] = useState('history');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ client_id: '', channel: 'email', subject: '', body: '' });
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [ruleForm, setRuleForm] = useState({
    name: '', reminder_type: 'vaccine', species: '', channel: 'email',
    days_before: 30, days_before_second: 7, days_after: 1, postal_template: '',
  });

  useEffect(() => {
    async function load() {
      try {
        const [cRes, rRes] = await Promise.all([
          communicationsAPI.list({}),
          communicationsAPI.listRules(),
        ]);
        setComms(cRes.data);
        setRules(rRes.data);
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, []);

  const handleSend = async (e) => {
    e.preventDefault();
    try {
      await communicationsAPI.send({
        ...form,
        client_id: parseInt(form.client_id),
      });
      toast.success('Message envoyé');
      setShowForm(false);
      const res = await communicationsAPI.list({});
      setComms(res.data);
    } catch {
      toast.error('Erreur d\'envoi');
    }
  };

  const handleRuleSubmit = async (e) => {
    e.preventDefault();
    try {
      await communicationsAPI.createRule({
        ...ruleForm,
        species: ruleForm.species || null,
        postal_template: ruleForm.postal_template || null,
      });
      toast.success('Regle creee');
      setShowRuleForm(false);
      setRuleForm({ name: '', reminder_type: 'vaccine', species: '', channel: 'email', days_before: 30, days_before_second: 7, days_after: 1, postal_template: '' });
      const res = await communicationsAPI.listRules();
      setRules(res.data);
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Communications</h1>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Envoyer un message</button>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'history' ? 'tab active' : 'tab'} onClick={() => setTab('history')}>Historique</button>
        <button className={tab === 'reminders' ? 'tab active' : 'tab'} onClick={() => setTab('reminders')}>Règles de rappel</button>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Envoyer un message</h3>
          <form onSubmit={handleSend}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">ID Client *</label>
                <input className="form-input" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Canal</label>
                <select className="form-select" value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })}>
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                  <option value="postal">Courrier postal</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Sujet</label>
              <input className="form-input" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Message *</label>
              <textarea className="form-textarea" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Envoyer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      {tab === 'history' && (
        <div className="card">
          <table>
            <thead><tr><th>Date</th><th>Client</th><th>Canal</th><th>Sujet</th><th>Statut</th></tr></thead>
            <tbody>
              {comms.map((c) => (
                <tr key={c.id}>
                  <td>{new Date(c.created_at).toLocaleDateString('fr-FR')}</td>
                  <td>{c.client_id}</td>
                  <td><span className={`badge badge-${c.channel === 'email' ? 'blue' : c.channel === 'postal' ? 'amber' : 'purple'}`}>{c.channel}</span></td>
                  <td>{c.subject || '-'}</td>
                  <td><span className={`badge badge-${c.status === 'sent' ? 'green' : c.status === 'failed' ? 'red' : 'amber'}`}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'reminders' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Regles de rappel</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowRuleForm(!showRuleForm)}>+ Nouvelle regle</button>
          </div>

          {showRuleForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleRuleSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Nom *</label>
                    <input className="form-input" value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Type</label>
                    <select className="form-select" value={ruleForm.reminder_type} onChange={(e) => setRuleForm({ ...ruleForm, reminder_type: e.target.value })}>
                      <option value="vaccine">Vaccination</option>
                      <option value="antiparasitic">Antiparasitaire</option>
                      <option value="checkup">Bilan de sante</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Canal</label>
                    <select className="form-select" value={ruleForm.channel} onChange={(e) => setRuleForm({ ...ruleForm, channel: e.target.value })}>
                      <option value="email">Email</option>
                      <option value="sms">SMS</option>
                      <option value="both">Email + SMS</option>
                      <option value="postal">Courrier postal</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Espece (optionnel)</label>
                    <select className="form-select" value={ruleForm.species} onChange={(e) => setRuleForm({ ...ruleForm, species: e.target.value })}>
                      <option value="">Toutes</option>
                      <option value="dog">Chien</option>
                      <option value="cat">Chat</option>
                      <option value="rabbit">Lapin</option>
                      <option value="bird">Oiseau</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">J- (1er rappel)</label>
                    <input type="number" className="form-input" value={ruleForm.days_before} onChange={(e) => setRuleForm({ ...ruleForm, days_before: parseInt(e.target.value) || 30 })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">J- (2e rappel)</label>
                    <input type="number" className="form-input" value={ruleForm.days_before_second} onChange={(e) => setRuleForm({ ...ruleForm, days_before_second: parseInt(e.target.value) || 7 })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">J+ (apres echeance)</label>
                    <input type="number" className="form-input" value={ruleForm.days_after} onChange={(e) => setRuleForm({ ...ruleForm, days_after: parseInt(e.target.value) || 1 })} />
                  </div>
                </div>
                {ruleForm.channel === 'postal' && (
                  <div className="form-group">
                    <label className="form-label">Template postal</label>
                    <textarea className="form-textarea" rows={4} value={ruleForm.postal_template} onChange={(e) => setRuleForm({ ...ruleForm, postal_template: e.target.value })}
                      placeholder="Cher(e) {client_name}, nous vous rappelons que {animal_name} doit recevoir son rappel de vaccination..." />
                  </div>
                )}
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Enregistrer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowRuleForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <table>
            <thead><tr><th>Nom</th><th>Type</th><th>Canal</th><th>J-30</th><th>J-7</th><th>J+1</th><th>Actif</th></tr></thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500 }}>{r.name}</td>
                  <td>{r.reminder_type}</td>
                  <td><span className={`badge badge-${r.channel === 'postal' ? 'amber' : 'blue'}`}>{r.channel}</span></td>
                  <td>{r.days_before}j</td>
                  <td>{r.days_before_second}j</td>
                  <td>{r.days_after}j</td>
                  <td><span className={`badge badge-${r.is_active ? 'green' : 'gray'}`}>{r.is_active ? 'Oui' : 'Non'}</span></td>
                </tr>
              ))}
              {rules.length === 0 && (
                <tr><td colSpan="7" className="table-empty">Aucune regle configuree</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
