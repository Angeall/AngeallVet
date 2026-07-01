import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { vaccinationsAPI, animalsAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

const emptyDose = () => ({ sequence: 0, label: '', valence: '', interval_days: 0, is_booster: false, booster_interval_days: 365 });
const emptyProtocol = () => ({ name: '', species: '', description: '', is_active: true, doses: [emptyDose()] });

export default function VaccinesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [tab, setTab] = useState('due');
  const [due, setDue] = useState([]);
  const [within, setWithin] = useState(30);
  const [protocols, setProtocols] = useState([]);
  const [species, setSpecies] = useState([]);
  const [form, setForm] = useState(null); // protocol editor

  const loadDue = useCallback(async () => {
    try { setDue((await vaccinationsAPI.due(within)).data || []); } catch (e) { toast.error('Erreur de chargement'); }
  }, [within]);
  const loadProtocols = useCallback(async () => {
    try { setProtocols((await vaccinationsAPI.listProtocols()).data || []); } catch {}
  }, []);

  useEffect(() => { loadDue(); }, [loadDue]);
  useEffect(() => { loadProtocols(); }, [loadProtocols]);
  useEffect(() => { animalsAPI.listSpecies().then((r) => setSpecies(r.data || [])).catch(() => {}); }, []);

  const speciesLabel = (code) => species.find((s) => s.code === code)?.label || code || 'Toutes';

  // ── protocol editor ──
  const startProtocol = (p) => setForm(p
    ? { id: p.id, name: p.name, species: p.species || '', description: p.description || '', is_active: p.is_active, doses: p.doses.length ? p.doses.map((d) => ({ ...d, valence: d.valence || '', booster_interval_days: d.booster_interval_days ?? 365 })) : [emptyDose()] }
    : emptyProtocol());
  const setDose = (i, patch) => setForm((f) => ({ ...f, doses: f.doses.map((d, idx) => (idx === i ? { ...d, ...patch } : d)) }));
  const addDose = () => setForm((f) => ({ ...f, doses: [...f.doses, { ...emptyDose(), sequence: f.doses.length }] }));
  const removeDose = (i) => setForm((f) => ({ ...f, doses: f.doses.filter((_, idx) => idx !== i) }));

  const saveProtocol = async (e) => {
    e.preventDefault();
    const payload = {
      name: form.name, species: form.species || null, description: form.description || null, is_active: form.is_active,
      doses: form.doses.map((d, i) => ({
        sequence: i, label: d.label, valence: d.valence || null,
        interval_days: parseInt(d.interval_days) || 0,
        is_booster: !!d.is_booster,
        booster_interval_days: d.is_booster ? (parseInt(d.booster_interval_days) || null) : null,
      })),
    };
    try {
      if (form.id) await vaccinationsAPI.updateProtocol(form.id, payload);
      else await vaccinationsAPI.createProtocol(payload);
      toast.success('Protocole enregistré');
      setForm(null);
      loadProtocols();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };
  const deleteProtocol = async (id) => {
    if (!window.confirm('Désactiver ce protocole ?')) return;
    try { await vaccinationsAPI.deleteProtocol(id); toast.success('Désactivé'); loadProtocols(); } catch { toast.error('Erreur'); }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Vaccins</h1>
          <span className="page-subtitle">Protocoles vaccinaux & rappels automatisés</span>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'due' ? 'tab active' : 'tab'} onClick={() => setTab('due')}>Rappels dus</button>
        {isAdmin && <button className={tab === 'protocols' ? 'tab active' : 'tab'} onClick={() => setTab('protocols')}>Protocoles</button>}
      </div>

      {tab === 'due' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <h3 className="card-title" style={{ margin: 0 }}>Rappels à venir & en retard</h3>
            <select className="form-select" style={{ width: 'auto' }} value={within} onChange={(e) => setWithin(parseInt(e.target.value))}>
              <option value={7}>7 jours</option>
              <option value={30}>30 jours</option>
              <option value={60}>60 jours</option>
              <option value={90}>90 jours</option>
            </select>
          </div>
          <div className="table-container">
            <table>
              <thead><tr><th>Échéance</th><th>Animal</th><th>Propriétaire</th><th>Valence</th><th>Statut</th></tr></thead>
              <tbody>
                {due.map((v) => (
                  <tr key={v.id}>
                    <td>{v.next_due_date}</td>
                    <td><Link to={`/animals/${v.animal_id}`} className="table-link" style={{ fontWeight: 600 }}>{v.animal_name}</Link></td>
                    <td>{v.client_id ? <Link to={`/clients/${v.client_id}`} className="table-link">{v.client_name}</Link> : v.client_name}</td>
                    <td>{v.valence}{v.next_label ? <span style={{ color: 'var(--gray-400)', marginLeft: '6px', fontSize: '0.8rem' }}>→ {v.next_label}</span> : ''}</td>
                    <td><span className={`badge badge-${v.overdue ? 'red' : 'amber'}`}>{v.overdue ? 'En retard' : 'À venir'}</span></td>
                  </tr>
                ))}
                {due.length === 0 && <tr><td colSpan="5" className="table-empty">Aucun rappel sur la période</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'protocols' && isAdmin && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Protocoles vaccinaux</h3>
            {!form && <button className="btn btn-primary btn-sm" onClick={() => startProtocol(null)}>+ Nouveau protocole</button>}
          </div>

          {form && (
            <form onSubmit={saveProtocol} style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2 }}>
                  <label className="form-label">Nom *</label>
                  <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Espèce</label>
                  <select className="form-select" value={form.species} onChange={(e) => setForm({ ...form, species: e.target.value })}>
                    <option value="">Toutes</option>
                    {species.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
                  </select>
                </div>
              </div>

              <label className="form-label" style={{ marginTop: '8px' }}>Doses (dans l'ordre)</label>
              {form.doses.map((d, i) => (
                <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', marginBottom: '8px', flexWrap: 'wrap' }}>
                  <div className="form-group" style={{ margin: 0, minWidth: '130px' }}>
                    <label className="form-label">Libellé</label>
                    <input className="form-input" value={d.label} onChange={(e) => setDose(i, { label: e.target.value })} placeholder="Primo 1" required />
                  </div>
                  <div className="form-group" style={{ margin: 0, minWidth: '110px' }}>
                    <label className="form-label">Valence</label>
                    <input className="form-input" value={d.valence} onChange={(e) => setDose(i, { valence: e.target.value })} placeholder="CHPPiL" />
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '110px' }}>
                    <label className="form-label">J+ (préc.)</label>
                    <input type="number" className="form-input" value={d.interval_days} onChange={(e) => setDose(i, { interval_days: e.target.value })} />
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.82rem', paddingBottom: '8px' }}>
                    <input type="checkbox" checked={!!d.is_booster} onChange={(e) => setDose(i, { is_booster: e.target.checked })} /> Rappel récurrent
                  </label>
                  {d.is_booster && (
                    <div className="form-group" style={{ margin: 0, maxWidth: '120px' }}>
                      <label className="form-label">Tous les (j)</label>
                      <input type="number" className="form-input" value={d.booster_interval_days} onChange={(e) => setDose(i, { booster_interval_days: e.target.value })} />
                    </div>
                  )}
                  {form.doses.length > 1 && <button type="button" className="btn btn-secondary btn-sm" style={{ color: 'var(--danger)' }} onClick={() => removeDose(i)}>X</button>}
                </div>
              ))}
              <button type="button" className="btn btn-secondary btn-sm" onClick={addDose} style={{ marginBottom: '12px' }}>+ Dose</button>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" className="btn btn-primary">Enregistrer</button>
                <button type="button" className="btn btn-secondary" onClick={() => setForm(null)}>Annuler</button>
              </div>
            </form>
          )}

          <div className="table-container">
            <table>
              <thead><tr><th>Nom</th><th>Espèce</th><th>Doses</th><th></th></tr></thead>
              <tbody>
                {protocols.filter((p) => p.is_active).map((p) => (
                  <tr key={p.id}>
                    <td><strong>{p.name}</strong></td>
                    <td>{speciesLabel(p.species)}</td>
                    <td style={{ fontSize: '0.82rem', color: 'var(--gray-600)' }}>
                      {p.doses.map((d, i) => (
                        <span key={i} className="badge badge-teal" style={{ marginRight: '4px' }}>
                          {d.label}{d.interval_days ? ` (J+${d.interval_days})` : ''}{d.is_booster ? ` ↻${d.booster_interval_days}j` : ''}
                        </span>
                      ))}
                    </td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => startProtocol(p)}>Modifier</button>
                      <button className="btn btn-secondary btn-sm" style={{ color: 'var(--danger)', marginLeft: '4px' }} onClick={() => deleteProtocol(p.id)}>Désactiver</button>
                    </td>
                  </tr>
                ))}
                {protocols.filter((p) => p.is_active).length === 0 && <tr><td colSpan="4" className="table-empty">Aucun protocole</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
