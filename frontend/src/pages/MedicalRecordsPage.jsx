import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { medicalAPI, animalsAPI, inventoryAPI } from '../services/api';
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
    subjective: '', objective: '', assessment: '', plan: '', home_treatment: '', notes: '',
    weight_kg: '',
  });

  // On-site treatment products
  const [onsiteProducts, setOnsiteProducts] = useState([]);
  const [onsiteProductSearch, setOnsiteProductSearch] = useState('');
  const [onsiteProductResults, setOnsiteProductResults] = useState([]);

  // Home treatment products
  const [htProducts, setHtProducts] = useState([]);
  const [htProductSearch, setHtProductSearch] = useState('');
  const [htProductResults, setHtProductResults] = useState([]);

  // Latest weight info
  const [latestWeight, setLatestWeight] = useState(null);

  // Dynamic species list
  const [speciesList, setSpeciesList] = useState([]);

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

  useEffect(() => {
    animalsAPI.listSpecies().then(res => setSpeciesList(res.data || [])).catch(() => {});
  }, []);

  // Load latest weight when animal_id changes
  useEffect(() => {
    if (!form.animal_id) { setLatestWeight(null); return; }
    const animalId = parseInt(form.animal_id);
    if (isNaN(animalId)) return;
    (async () => {
      try {
        const res = await animalsAPI.getLatestWeight(animalId);
        setLatestWeight(res.data);
      } catch {
        setLatestWeight(null);
      }
    })();
  }, [form.animal_id]);

  // Product search debounce for on-site treatment
  useEffect(() => {
    if (onsiteProductSearch.length < 2) { setOnsiteProductResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await inventoryAPI.listProducts({ search: onsiteProductSearch });
        setOnsiteProductResults(res.data || []);
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [onsiteProductSearch]);

  // Product search debounce for home treatment
  useEffect(() => {
    if (htProductSearch.length < 2) { setHtProductResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await inventoryAPI.listProducts({ search: htProductSearch });
        setHtProductResults(res.data || []);
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [htProductSearch]);

  const addOnsiteProduct = (product) => {
    setOnsiteProducts(prev => [...prev, { product_id: product.id, name: product.name, quantity: 1, selling_price: product.selling_price }]);
    setOnsiteProductSearch(''); setOnsiteProductResults([]);
  };
  const removeOnsiteProduct = (idx) => setOnsiteProducts(prev => prev.filter((_, i) => i !== idx));
  const updateOnsiteProductQty = (idx, qty) => {
    setOnsiteProducts(prev => { const u = [...prev]; u[idx] = { ...u[idx], quantity: parseFloat(qty) || 1 }; return u; });
  };

  const addHtProduct = (product) => {
    setHtProducts(prev => [...prev, { product_id: product.id, name: product.name, quantity: 1, selling_price: product.selling_price }]);
    setHtProductSearch('');
    setHtProductResults([]);
  };

  const removeHtProduct = (idx) => {
    setHtProducts(prev => prev.filter((_, i) => i !== idx));
  };

  const updateHtProductQty = (idx, qty) => {
    setHtProducts(prev => {
      const updated = [...prev];
      updated[idx] = { ...updated[idx], quantity: parseFloat(qty) || 1 };
      return updated;
    });
  };

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
      if (t.products) {
        setOnsiteProducts(t.products.filter(p => p.treatment_location === 'onsite').map(p => ({ product_id: p.product_id, quantity: parseFloat(p.quantity), product_name: '' })));
        setHtProducts(t.products.filter(p => p.treatment_location === 'home').map(p => ({ product_id: p.product_id, quantity: parseFloat(p.quantity), product_name: '' })));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        animal_id: parseInt(form.animal_id),
        weight_kg: form.weight_kg ? parseFloat(form.weight_kg) : null,
        onsite_treatment_products: onsiteProducts.map(p => ({ product_id: p.product_id, quantity: p.quantity })),
        home_treatment_products: htProducts.map(p => ({ product_id: p.product_id, quantity: p.quantity })),
      };
      await medicalAPI.createRecord(payload);
      toast.success('Dossier medical cree');
      setShowForm(false);
      setOnsiteProducts([]);
      setHtProducts([]);
      setLatestWeight(null);
      setForm({
        animal_id: '', record_type: 'consultation',
        subjective: '', objective: '', assessment: '', plan: '', home_treatment: '', notes: '',
        weight_kg: '',
      });
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  const handleCreateInvoice = async (recordId) => {
    try {
      await medicalAPI.createInvoiceFromRecord(recordId);
      toast.success('Facture brouillon creee');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors de la creation de la facture');
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

                {/* Weight input */}
                <div className="form-row">
                  <div className="form-group" style={{ maxWidth: '200px' }}>
                    <label className="form-label">Poids (kg)</label>
                    <input type="number" step="0.01" className="form-input" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })} placeholder="Ex: 12.50" />
                  </div>
                  {latestWeight && (
                    <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: '8px' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                        Dernier poids: <strong>{parseFloat(latestWeight.weight_kg).toFixed(2)} kg</strong>
                        {form.weight_kg && (
                          <span style={{ marginLeft: '8px', color: parseFloat(form.weight_kg) > parseFloat(latestWeight.weight_kg) ? 'var(--green-600)' : parseFloat(form.weight_kg) < parseFloat(latestWeight.weight_kg) ? 'var(--danger)' : 'var(--gray-400)' }}>
                            ({(parseFloat(form.weight_kg) - parseFloat(latestWeight.weight_kg) >= 0 ? '+' : '')}{(parseFloat(form.weight_kg) - parseFloat(latestWeight.weight_kg)).toFixed(2)} kg)
                          </span>
                        )}
                      </span>
                    </div>
                  )}
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
                {/* P - Sur place: products first, then notes */}
                <div style={{ borderTop: '1px solid var(--gray-200)', margin: '16px 0', paddingTop: '16px' }}>
                  <h4 style={{ marginBottom: '8px' }}>P - Produits / Actes sur place</h4>
                  <div className="form-group" style={{ position: 'relative' }}>
                    <label className="form-label">Ajouter un produit / acte</label>
                    <input
                      className="form-input"
                      placeholder="Rechercher un acte / medicament utilise sur place..."
                      value={onsiteProductSearch}
                      onChange={(e) => setOnsiteProductSearch(e.target.value)}
                      onBlur={() => setTimeout(() => setOnsiteProductResults([]), 200)}
                    />
                    {onsiteProductResults.length > 0 && (
                      <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                        {onsiteProductResults.map(p => (
                          <div key={p.id} onMouseDown={() => addOnsiteProduct(p)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                            onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                            onMouseLeave={(e) => e.target.style.background = 'white'}>
                            <strong>{p.name}</strong>
                            <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{parseFloat(p.selling_price || 0).toFixed(2)} EUR</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {onsiteProducts.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      {onsiteProducts.map((p, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px', padding: '6px 8px', background: 'var(--gray-50)', borderRadius: '6px' }}>
                          <span style={{ flex: 1 }}>{p.name}</span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>{parseFloat(p.selling_price || 0).toFixed(2)} EUR</span>
                          <input type="number" min="1" step="1" style={{ width: '60px' }} className="form-input" value={p.quantity} onChange={(e) => updateOnsiteProductQty(idx, e.target.value)} />
                          <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeOnsiteProduct(idx)} style={{ color: 'var(--danger)' }}>X</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="form-group" style={{ marginTop: '12px' }}>
                    <label className="form-label">Notes supplementaires sur place</label>
                    <textarea className="form-textarea" value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })} placeholder="Actes realises en clinique..." />
                  </div>
                </div>

                {/* A domicile: products first, then notes */}
                <div style={{ borderTop: '1px solid var(--gray-200)', margin: '16px 0', paddingTop: '16px' }}>
                  <h4 style={{ marginBottom: '8px' }}>Produits / Medicaments a domicile</h4>
                  <div className="form-group" style={{ position: 'relative' }}>
                    <label className="form-label">Ajouter un produit</label>
                    <input
                      className="form-input"
                      placeholder="Rechercher un medicament a emporter..."
                      value={htProductSearch}
                      onChange={(e) => setHtProductSearch(e.target.value)}
                      onBlur={() => setTimeout(() => setHtProductResults([]), 200)}
                    />
                    {htProductResults.length > 0 && (
                      <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                        {htProductResults.map(p => (
                          <div key={p.id} onMouseDown={() => addHtProduct(p)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                            onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                            onMouseLeave={(e) => e.target.style.background = 'white'}>
                            <strong>{p.name}</strong>
                            <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{parseFloat(p.selling_price || 0).toFixed(2)} EUR</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {htProducts.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      {htProducts.map((p, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px', padding: '6px 8px', background: 'var(--gray-50)', borderRadius: '6px' }}>
                          <span style={{ flex: 1 }}>{p.name}</span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>{parseFloat(p.selling_price || 0).toFixed(2)} EUR</span>
                          <input type="number" min="1" step="1" style={{ width: '60px' }} className="form-input" value={p.quantity} onChange={(e) => updateHtProductQty(idx, e.target.value)} />
                          <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeHtProduct(idx)} style={{ color: 'var(--danger)' }}>X</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="form-group" style={{ marginTop: '12px' }}>
                    <label className="form-label">Notes supplementaires domicile</label>
                    <textarea className="form-textarea" value={form.home_treatment} onChange={(e) => setForm({ ...form, home_treatment: e.target.value })} placeholder="Instructions pour le proprietaire..." />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                  <button type="submit" className="btn btn-primary">Enregistrer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <div className="card">
            <table>
              <thead>
                <tr><th>Date</th><th>Type</th><th>Animal ID</th><th>Motif</th><th>Diagnostic</th><th>Actions</th></tr>
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
                    <td>
                      {r.home_treatment_products && r.home_treatment_products.length > 0 && (
                        <button className="btn btn-secondary btn-sm" onClick={() => handleCreateInvoice(r.id)}>
                          Creer facture
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {records.length === 0 && (
                  <tr><td colSpan="6" className="table-empty">Aucun dossier</td></tr>
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
                      {speciesList.map(s => <option key={s.code} value={s.code}>{s.label}</option>)}
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
