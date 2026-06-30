import React, { useState, useEffect, useCallback } from 'react';
import { commissionsAPI, inventoryAPI } from '../services/api';
import toast from 'react-hot-toast';

const SCOPES = { all: 'Tout', category: 'Catégorie', product: 'Produit précis' };
const PRODUCT_TYPES = { medication: 'Médicament', food: 'Aliment', supply: 'Fourniture', service: 'Acte' };
const BASES = { profit: '% du bénéfice', revenue: '% du CA', per_unit: 'Forfait / unité (€)', per_line: 'Forfait / ligne (€)' };
const WEEKDAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

const emptyComponent = () => ({ scope: 'all', product_type: 'medication', product_id: null, basis: 'revenue', value: 0 });
const emptyRule = () => ({ name: '', description: '', is_active: true, components: [emptyComponent()] });

export default function BillingRulesPage() {
  const [rules, setRules] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [vets, setVets] = useState([]);
  const [products, setProducts] = useState([]);

  const [ruleForm, setRuleForm] = useState(null); // {id?, ...emptyRule}
  const [programForm, setProgramForm] = useState(null); // {id?, name, days: {0..6: rule_id|null}}

  const load = useCallback(async () => {
    try {
      const [r, p, v] = await Promise.all([
        commissionsAPI.listRules(),
        commissionsAPI.listPrograms(),
        commissionsAPI.listVets(),
      ]);
      setRules(r.data || []);
      setPrograms(p.data || []);
      setVets(v.data || []);
    } catch { toast.error('Erreur de chargement'); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    inventoryAPI.listProducts({ limit: 500 }).then((res) => setProducts(res.data || [])).catch(() => {});
  }, []);

  const ruleName = (id) => rules.find((r) => r.id === id)?.name || '—';

  // ── Rule form ──
  const startRule = (rule) => setRuleForm(rule
    ? { id: rule.id, name: rule.name, description: rule.description || '', is_active: rule.is_active, components: rule.components.length ? rule.components.map((c) => ({ ...c })) : [emptyComponent()] }
    : emptyRule());

  const setComp = (idx, patch) => setRuleForm((f) => ({ ...f, components: f.components.map((c, i) => (i === idx ? { ...c, ...patch } : c)) }));
  const addComp = () => setRuleForm((f) => ({ ...f, components: [...f.components, emptyComponent()] }));
  const removeComp = (idx) => setRuleForm((f) => ({ ...f, components: f.components.filter((_, i) => i !== idx) }));

  const saveRule = async (e) => {
    e.preventDefault();
    const payload = {
      name: ruleForm.name,
      description: ruleForm.description || null,
      is_active: ruleForm.is_active,
      components: ruleForm.components.map((c) => ({
        scope: c.scope,
        product_type: c.scope === 'category' ? c.product_type : null,
        product_id: c.scope === 'product' ? (c.product_id ? parseInt(c.product_id) : null) : null,
        basis: c.basis,
        value: parseFloat(c.value) || 0,
      })),
    };
    try {
      if (ruleForm.id) await commissionsAPI.updateRule(ruleForm.id, payload);
      else await commissionsAPI.createRule(payload);
      toast.success('Règle enregistrée');
      setRuleForm(null);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };

  const deleteRule = async (id) => {
    if (!confirm('Désactiver cette règle ?')) return;
    try { await commissionsAPI.deleteRule(id); toast.success('Règle désactivée'); load(); } catch { toast.error('Erreur'); }
  };

  // ── Program form ──
  const startProgram = (program) => {
    const days = {};
    for (let d = 0; d < 7; d++) days[d] = null;
    if (program) program.days.forEach((d) => { days[d.weekday] = d.rule_id; });
    setProgramForm({ id: program?.id, name: program?.name || '', days });
  };

  const saveProgram = async (e) => {
    e.preventDefault();
    const payload = {
      name: programForm.name,
      is_active: true,
      days: Object.entries(programForm.days)
        .filter(([, ruleId]) => ruleId)
        .map(([weekday, ruleId]) => ({ weekday: parseInt(weekday), rule_id: parseInt(ruleId) })),
    };
    try {
      if (programForm.id) await commissionsAPI.updateProgram(programForm.id, payload);
      else await commissionsAPI.createProgram(payload);
      toast.success('Programme enregistré');
      setProgramForm(null);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || 'Erreur'); }
  };

  const deleteProgram = async (id) => {
    if (!confirm('Désactiver ce programme ?')) return;
    try { await commissionsAPI.deleteProgram(id); toast.success('Programme désactivé'); load(); } catch { toast.error('Erreur'); }
  };

  const assignProgram = async (userId, programId) => {
    try {
      await commissionsAPI.assignProgram(userId, programId ? parseInt(programId) : null);
      toast.success('Programme affecté');
      setVets((vs) => vs.map((v) => (v.id === userId ? { ...v, billing_program_id: programId ? parseInt(programId) : null } : v)));
    } catch { toast.error('Erreur'); }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Règles de facturation</h1>
          <p className="page-subtitle">Commissions des vétérinaires (calculées sur l'encaissé)</p>
        </div>
      </div>

      {/* ── Rules ── */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Règles</h3>
          {!ruleForm && <button className="btn btn-primary btn-sm" onClick={() => startRule(null)}>+ Nouvelle règle</button>}
        </div>

        {ruleForm && (
          <form onSubmit={saveRule} style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Nom *</label>
                <input className="form-input" value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} required />
              </div>
              <div className="form-group" style={{ flex: 3 }}>
                <label className="form-label">Description</label>
                <input className="form-input" value={ruleForm.description} onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })} />
              </div>
            </div>

            <label className="form-label" style={{ marginTop: '8px' }}>Composants</label>
            {ruleForm.components.map((c, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', marginBottom: '8px', flexWrap: 'wrap' }}>
                <div className="form-group" style={{ margin: 0, minWidth: '130px' }}>
                  <label className="form-label">Périmètre</label>
                  <select className="form-select" value={c.scope} onChange={(e) => setComp(idx, { scope: e.target.value })}>
                    {Object.entries(SCOPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                {c.scope === 'category' && (
                  <div className="form-group" style={{ margin: 0, minWidth: '130px' }}>
                    <label className="form-label">Catégorie</label>
                    <select className="form-select" value={c.product_type} onChange={(e) => setComp(idx, { product_type: e.target.value })}>
                      {Object.entries(PRODUCT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </div>
                )}
                {c.scope === 'product' && (
                  <div className="form-group" style={{ margin: 0, minWidth: '180px' }}>
                    <label className="form-label">Produit</label>
                    <select className="form-select" value={c.product_id || ''} onChange={(e) => setComp(idx, { product_id: e.target.value })}>
                      <option value="">-- Choisir --</option>
                      {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>
                )}
                <div className="form-group" style={{ margin: 0, minWidth: '150px' }}>
                  <label className="form-label">Base</label>
                  <select className="form-select" value={c.basis} onChange={(e) => setComp(idx, { basis: e.target.value })}>
                    {Object.entries(BASES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ margin: 0, maxWidth: '90px' }}>
                  <label className="form-label">Valeur</label>
                  <input type="number" step="0.01" className="form-input" value={c.value} onChange={(e) => setComp(idx, { value: e.target.value })} />
                </div>
                {ruleForm.components.length > 1 && (
                  <button type="button" className="btn btn-secondary btn-sm" style={{ color: 'var(--danger)' }} onClick={() => removeComp(idx)}>X</button>
                )}
              </div>
            ))}
            <button type="button" className="btn btn-secondary btn-sm" onClick={addComp} style={{ marginBottom: '12px' }}>+ Composant</button>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setRuleForm(null)}>Annuler</button>
            </div>
          </form>
        )}

        <div className="table-container">
          <table>
            <thead><tr><th>Nom</th><th>Composants</th><th></th></tr></thead>
            <tbody>
              {rules.filter((r) => r.is_active).map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.name}</strong>{r.description && <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>{r.description}</div>}</td>
                  <td style={{ fontSize: '0.82rem', color: 'var(--gray-600)' }}>
                    {r.components.map((c, i) => (
                      <span key={i} className="badge badge-teal" style={{ marginRight: '4px' }}>
                        {c.scope === 'product' ? (products.find((p) => p.id === c.product_id)?.name || 'Produit') : c.scope === 'category' ? PRODUCT_TYPES[c.product_type] : 'Tout'}
                        {' · '}{BASES[c.basis].replace(' du', '').replace(' / ', '/')} {c.value}
                      </span>
                    ))}
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => startRule(r)}>Modifier</button>
                    <button className="btn btn-secondary btn-sm" style={{ color: 'var(--danger)', marginLeft: '4px' }} onClick={() => deleteRule(r.id)}>Désactiver</button>
                  </td>
                </tr>
              ))}
              {rules.filter((r) => r.is_active).length === 0 && <tr><td colSpan="3" className="table-empty">Aucune règle</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Programs ── */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Programmes hebdomadaires</h3>
          {!programForm && <button className="btn btn-primary btn-sm" onClick={() => startProgram(null)}>+ Nouveau programme</button>}
        </div>

        {programForm && (
          <form onSubmit={saveProgram} style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <div className="form-group">
              <label className="form-label">Nom *</label>
              <input className="form-input" value={programForm.name} onChange={(e) => setProgramForm({ ...programForm, name: e.target.value })} required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', marginBottom: '12px' }}>
              {WEEKDAYS.map((label, d) => (
                <div className="form-group" key={d} style={{ margin: 0 }}>
                  <label className="form-label">{label}</label>
                  <select className="form-select" value={programForm.days[d] || ''} onChange={(e) => setProgramForm({ ...programForm, days: { ...programForm.days, [d]: e.target.value || null } })}>
                    <option value="">— Aucune —</option>
                    {rules.filter((r) => r.is_active).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setProgramForm(null)}>Annuler</button>
            </div>
          </form>
        )}

        <div className="table-container">
          <table>
            <thead><tr><th>Nom</th>{WEEKDAYS.map((d) => <th key={d}>{d.slice(0, 3)}</th>)}<th></th></tr></thead>
            <tbody>
              {programs.filter((p) => p.is_active).map((p) => {
                const byDay = {};
                p.days.forEach((d) => { byDay[d.weekday] = d.rule_id; });
                return (
                  <tr key={p.id}>
                    <td><strong>{p.name}</strong></td>
                    {WEEKDAYS.map((_, d) => <td key={d} style={{ fontSize: '0.8rem' }}>{byDay[d] ? ruleName(byDay[d]) : '—'}</td>)}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => startProgram(p)}>Modifier</button>
                      <button className="btn btn-secondary btn-sm" style={{ color: 'var(--danger)', marginLeft: '4px' }} onClick={() => deleteProgram(p.id)}>Désactiver</button>
                    </td>
                  </tr>
                );
              })}
              {programs.filter((p) => p.is_active).length === 0 && <tr><td colSpan="9" className="table-empty">Aucun programme</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Vet assignment ── */}
      <div className="card">
        <div className="card-header"><h3 className="card-title">Affectation des vétérinaires</h3></div>
        <div className="table-container">
          <table>
            <thead><tr><th>Vétérinaire</th><th>Programme par défaut</th></tr></thead>
            <tbody>
              {vets.map((v) => (
                <tr key={v.id}>
                  <td>{v.name}</td>
                  <td>
                    <select className="form-select" style={{ maxWidth: '260px' }} value={v.billing_program_id || ''} onChange={(e) => assignProgram(v.id, e.target.value)}>
                      <option value="">— Aucun —</option>
                      {programs.filter((p) => p.is_active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {vets.length === 0 && <tr><td colSpan="2" className="table-empty">Aucun vétérinaire</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
