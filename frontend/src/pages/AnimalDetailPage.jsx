import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { animalsAPI, medicalAPI, hospitalizationAPI, billingAPI, inventoryAPI, communicationsAPI } from '../services/api';
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
  const [showEditForm, setShowEditForm] = useState(false);
  const [showInvoiceForm, setShowInvoiceForm] = useState(false);
  const [recordForm, setRecordForm] = useState({
    record_type: 'consultation', subjective: '', objective: '', assessment: '', plan: '', home_treatment: '', notes: '',
  });
  const [hospForm, setHospForm] = useState({ reason: '', cage_number: '' });
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [alertForm, setAlertForm] = useState({ alert_type: 'allergy', message: '', severity: 'warning' });
  const [editForm, setEditForm] = useState({});
  const [products, setProducts] = useState([]);
  const [invoiceLines, setInvoiceLines] = useState([{ description: '', quantity: '1', unit_price: '', vat_rate: '20.00', product_id: null }]);

  const defaultPrices = [
    { label: 'Consultation', price: '40.00', vat: '20.00' },
    { label: 'Vaccination', price: '55.00', vat: '20.00' },
    { label: 'Detartrage', price: '120.00', vat: '20.00' },
    { label: 'Sterilisation chat', price: '150.00', vat: '20.00' },
    { label: 'Sterilisation chien', price: '250.00', vat: '20.00' },
    { label: 'Analyse sanguine', price: '85.00', vat: '20.00' },
  ];

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
      setEditForm({
        name: aRes.data.name, species: aRes.data.species, breed: aRes.data.breed || '',
        sex: aRes.data.sex, date_of_birth: aRes.data.date_of_birth || '', color: aRes.data.color || '',
        microchip_number: aRes.data.microchip_number || '', tattoo_number: aRes.data.tattoo_number || '',
        is_neutered: aRes.data.is_neutered, notes: aRes.data.notes || '',
      });
    } catch { toast.error('Erreur de chargement'); }
  };

  useEffect(() => { load(); }, [id]);

  const loadProducts = async () => {
    try { const res = await inventoryAPI.listProducts({}); setProducts(res.data || []); } catch {}
  };

  const addWeight = async (e) => {
    e.preventDefault();
    if (!newWeight) return;
    try {
      await animalsAPI.addWeight(id, { weight_kg: parseFloat(newWeight) });
      const wRes = await animalsAPI.getWeights(id);
      setWeights(wRes.data); setNewWeight(''); toast.success('Poids enregistre');
    } catch { toast.error('Erreur'); }
  };

  const applyTemplate = (templateId) => {
    const t = templates.find((tp) => tp.id === parseInt(templateId));
    if (t) setRecordForm({ ...recordForm, subjective: t.subjective || '', objective: t.objective || '', assessment: t.assessment || '', plan: t.plan || '' });
  };

  const handleRecordSubmit = async (e) => {
    e.preventDefault();
    try {
      await medicalAPI.createRecord({ ...recordForm, animal_id: parseInt(id) });
      toast.success('Dossier medical cree'); setShowRecordForm(false);
      setRecordForm({ record_type: 'consultation', subjective: '', objective: '', assessment: '', plan: '', home_treatment: '', notes: '' });
      const rRes = await medicalAPI.listRecords({ animal_id: id }); setRecords(rRes.data);
    } catch { toast.error('Erreur lors de la creation'); }
  };

  const sendHomeTreatment = async (record) => {
    if (!animal.client_id) { toast.error('Pas de client associe'); return; }
    try {
      await communicationsAPI.send({
        client_id: animal.client_id, channel: 'email',
        subject: `Traitement a la maison pour ${animal.name}`,
        body: `Bonjour,\n\nVoici les instructions de traitement pour ${animal.name} :\n\n${record.home_treatment || record.plan || ''}\n\nN'hesitez pas a nous contacter.\n\nCordialement,\nClinique AngeallVet`,
      });
      toast.success('Email envoye au client');
    } catch { toast.error('Erreur d\'envoi'); }
  };

  const activeHosp = hospitalizations.find((h) => h.status === 'active');

  const handleHospitalize = async (e) => {
    e.preventDefault();
    try {
      await hospitalizationAPI.create({ animal_id: parseInt(id), reason: hospForm.reason, cage_number: hospForm.cage_number || null });
      toast.success('Animal hospitalise'); setShowHospForm(false); setHospForm({ reason: '', cage_number: '' }); load();
    } catch { toast.error('Erreur'); }
  };

  const handleDischarge = async () => {
    if (!activeHosp) return;
    try { await hospitalizationAPI.update(activeHosp.id, { status: 'discharged' }); toast.success('Animal sorti'); load(); } catch { toast.error('Erreur'); }
  };

  const handleAlertSubmit = async (e) => {
    e.preventDefault();
    try { await animalsAPI.addAlert(id, alertForm); toast.success('Alerte ajoutee'); setShowAlertForm(false); setAlertForm({ alert_type: 'allergy', message: '', severity: 'warning' }); load(); } catch { toast.error('Erreur'); }
  };

  const removeAlert = async (alertId) => {
    try { await animalsAPI.removeAlert(id, alertId); toast.success('Alerte supprimee'); load(); } catch { toast.error('Erreur'); }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      await animalsAPI.update(id, { ...editForm, date_of_birth: editForm.date_of_birth || null, microchip_number: editForm.microchip_number || null, tattoo_number: editForm.tattoo_number || null, notes: editForm.notes || null });
      toast.success('Animal mis a jour'); setShowEditForm(false); load();
    } catch { toast.error('Erreur'); }
  };

  const addInvoiceLine = () => setInvoiceLines([...invoiceLines, { description: '', quantity: '1', unit_price: '', vat_rate: '20.00', product_id: null }]);
  const removeInvoiceLine = (idx) => { if (invoiceLines.length > 1) setInvoiceLines(invoiceLines.filter((_, i) => i !== idx)); };
  const updateInvoiceLine = (idx, field, value) => { const l = [...invoiceLines]; l[idx][field] = value; setInvoiceLines(l); };
  const addDefaultPrice = (dp) => { setInvoiceLines([...invoiceLines.filter(l => l.description), { description: dp.label, quantity: '1', unit_price: dp.price, vat_rate: dp.vat, product_id: null }]); };
  const addProductLine = (product) => { setInvoiceLines([...invoiceLines.filter(l => l.description), { description: product.name, quantity: '1', unit_price: parseFloat(product.selling_price).toFixed(2), vat_rate: parseFloat(product.vat_rate).toFixed(2), product_id: product.id }]); };

  const handleInvoiceSubmit = async (e) => {
    e.preventDefault();
    try {
      await billingAPI.createInvoice({
        client_id: animal.client_id, animal_id: parseInt(id),
        lines: invoiceLines.filter(l => l.description).map(l => ({ description: l.description, quantity: parseFloat(l.quantity), unit_price: parseFloat(l.unit_price), vat_rate: parseFloat(l.vat_rate), product_id: l.product_id })),
      });
      toast.success('Facture creee'); setShowInvoiceForm(false);
      setInvoiceLines([{ description: '', quantity: '1', unit_price: '', vat_rate: '20.00', product_id: null }]);
    } catch { toast.error('Erreur'); }
  };

  if (!animal) return <div className="page-content">Chargement...</div>;

  const alertTypeLabels = { allergy: 'Allergie', aggressive: 'Agressif', chronic: 'Maladie chronique', medication: 'Medicament', other: 'Autre' };
  const severityLabels = { danger: 'Danger', warning: 'Attention', info: 'Information' };
  const weightChartData = [...weights].reverse().map(w => ({ date: new Date(w.recorded_at).toLocaleDateString('fr-FR'), poids: parseFloat(w.weight_kg) }));
  const recordTypeLabel = { consultation: 'Consultation', vaccination: 'Vaccination', surgery: 'Chirurgie', lab_result: 'Labo', imaging: 'Imagerie', note: 'Note' };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/animals" className="breadcrumb-link">Animaux /</Link>
          <h1 className="page-title">{animal.name}</h1>
          {animal.client_id && <Link to={`/clients/${animal.client_id}`} className="breadcrumb-link" style={{ marginLeft: '12px', fontSize: '0.85rem' }}>Voir le client</Link>}
        </div>
        <div className="page-header-actions" style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => { setShowInvoiceForm(!showInvoiceForm); if (!showInvoiceForm) loadProducts(); }}>Facturer</button>
          {activeHosp ? (
            <>
              <Link to={`/hospitalization/${activeHosp.id}`} className="btn btn-primary btn-sm">Voir l'hospitalisation</Link>
              <button className="btn btn-secondary btn-sm" onClick={handleDischarge}>Sortie</button>
            </>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={() => setShowHospForm(!showHospForm)}>Hospitaliser</button>
          )}
        </div>
      </div>

      {activeHosp && (
        <Link to={`/hospitalization/${activeHosp.id}`} style={{ textDecoration: 'none' }}>
          <div className="alert-banner warning">Actuellement hospitalise - Cage {activeHosp.cage_number || 'N/A'} - {activeHosp.reason}</div>
        </Link>
      )}

      {showHospForm && !activeHosp && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Hospitaliser {animal.name}</h3>
          <form onSubmit={handleHospitalize}>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Motif *</label><textarea className="form-textarea" value={hospForm.reason} onChange={(e) => setHospForm({ ...hospForm, reason: e.target.value })} required /></div>
              <div className="form-group"><label className="form-label">Cage</label><input className="form-input" value={hospForm.cage_number} onChange={(e) => setHospForm({ ...hospForm, cage_number: e.target.value })} /></div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}><button type="submit" className="btn btn-primary">Hospitaliser</button><button type="button" className="btn btn-secondary" onClick={() => setShowHospForm(false)}>Annuler</button></div>
          </form>
        </div>
      )}

      {showInvoiceForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Facturation rapide - {animal.name}</h3>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {defaultPrices.map((dp, i) => (<button key={i} type="button" className="btn btn-secondary btn-sm" onClick={() => addDefaultPrice(dp)}>{dp.label} ({dp.price} EUR)</button>))}
          </div>
          {products.length > 0 && (
            <div style={{ marginBottom: '12px' }}><label className="form-label">Ajouter un produit:</label>
              <select className="form-select" onChange={(e) => { const p = products.find(pr => pr.id === parseInt(e.target.value)); if (p) addProductLine(p); e.target.value = ''; }}>
                <option value="">-- Choisir --</option>{products.map(p => <option key={p.id} value={p.id}>{p.name} - {parseFloat(p.selling_price).toFixed(2)} EUR</option>)}
              </select>
            </div>
          )}
          <form onSubmit={handleInvoiceSubmit}>
            {invoiceLines.map((line, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', marginBottom: '8px' }}>
                <div className="form-group" style={{ flex: 1 }}><input className="form-input" placeholder="Description" value={line.description} onChange={(e) => updateInvoiceLine(idx, 'description', e.target.value)} required /></div>
                <div className="form-group" style={{ maxWidth: '70px' }}><input type="number" className="form-input" placeholder="Qte" value={line.quantity} onChange={(e) => updateInvoiceLine(idx, 'quantity', e.target.value)} /></div>
                <div className="form-group" style={{ maxWidth: '110px' }}><input type="number" step="0.01" className="form-input" placeholder="Prix HT" value={line.unit_price} onChange={(e) => updateInvoiceLine(idx, 'unit_price', e.target.value)} required /></div>
                <div className="form-group" style={{ maxWidth: '70px' }}><input type="number" className="form-input" placeholder="TVA%" value={line.vat_rate} onChange={(e) => updateInvoiceLine(idx, 'vat_rate', e.target.value)} /></div>
                {invoiceLines.length > 1 && <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeInvoiceLine(idx)}>X</button>}
              </div>
            ))}
            <button type="button" className="btn btn-secondary btn-sm" onClick={addInvoiceLine} style={{ marginBottom: '12px' }}>+ Ligne</button>
            <div style={{ display: 'flex', gap: '8px' }}><button type="submit" className="btn btn-primary">Creer la facture</button><button type="button" className="btn btn-secondary" onClick={() => setShowInvoiceForm(false)}>Annuler</button></div>
          </form>
        </div>
      )}

      {/* Alerts */}
      <div className="card">
        <div className="card-header"><h3 className="card-title">Alertes</h3><button className="btn btn-primary btn-sm" onClick={() => setShowAlertForm(!showAlertForm)}>+ Ajouter</button></div>
        {showAlertForm && (
          <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            <form onSubmit={handleAlertSubmit}>
              <div className="form-row">
                <div className="form-group"><label className="form-label">Type *</label><select className="form-select" value={alertForm.alert_type} onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}>{Object.entries(alertTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
                <div className="form-group"><label className="form-label">Severite</label><select className="form-select" value={alertForm.severity} onChange={(e) => setAlertForm({ ...alertForm, severity: e.target.value })}>{Object.entries(severityLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
              </div>
              <div className="form-group"><label className="form-label">Message *</label><input className="form-input" value={alertForm.message} onChange={(e) => setAlertForm({ ...alertForm, message: e.target.value })} required /></div>
              <div style={{ display: 'flex', gap: '8px' }}><button type="submit" className="btn btn-primary">Ajouter</button><button type="button" className="btn btn-secondary" onClick={() => setShowAlertForm(false)}>Annuler</button></div>
            </form>
          </div>
        )}
        {animal.alerts?.filter(a => a.is_active).length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {animal.alerts.filter(a => a.is_active).map(alert => (
              <div key={alert.id} className={`alert-banner ${alert.severity}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: 0 }}>
                <span><strong>{alertTypeLabels[alert.alert_type] || alert.alert_type}:</strong> {alert.message}</span>
                <button className="btn btn-sm" onClick={() => removeAlert(alert.id)} style={{ background: 'rgba(255,255,255,0.3)', border: 'none', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px' }}>X</button>
              </div>
            ))}
          </div>
        ) : <p style={{ color: 'var(--gray-400)', textAlign: 'center', margin: '8px 0' }}>Aucune alerte active</p>}
      </div>

      {/* Info card with edit */}
      <div className="card">
        <div className="card-header"><h3 className="card-title">Informations</h3><button className="btn btn-secondary btn-sm" onClick={() => setShowEditForm(!showEditForm)}>{showEditForm ? 'Annuler' : 'Modifier'}</button></div>
        {showEditForm ? (
          <form onSubmit={handleEditSubmit}>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Nom *</label><input className="form-input" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} required /></div>
              <div className="form-group"><label className="form-label">Espece</label><select className="form-select" value={editForm.species} onChange={(e) => setEditForm({ ...editForm, species: e.target.value })}><option value="dog">Chien</option><option value="cat">Chat</option><option value="bird">Oiseau</option><option value="rabbit">Lapin</option><option value="reptile">Reptile</option><option value="horse">Cheval</option><option value="nac">NAC</option></select></div>
              <div className="form-group"><label className="form-label">Race</label><input className="form-input" value={editForm.breed} onChange={(e) => setEditForm({ ...editForm, breed: e.target.value })} /></div>
            </div>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Sexe</label><select className="form-select" value={editForm.sex} onChange={(e) => setEditForm({ ...editForm, sex: e.target.value })}><option value="male">Male</option><option value="female">Femelle</option></select></div>
              <div className="form-group"><label className="form-label">Date de naissance</label><input type="date" className="form-input" value={editForm.date_of_birth} onChange={(e) => setEditForm({ ...editForm, date_of_birth: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">Couleur</label><input className="form-input" value={editForm.color} onChange={(e) => setEditForm({ ...editForm, color: e.target.value })} /></div>
            </div>
            <div className="form-row">
              <div className="form-group"><label className="form-label">N Puce</label><input className="form-input" value={editForm.microchip_number} onChange={(e) => setEditForm({ ...editForm, microchip_number: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">N Tatouage</label><input className="form-input" value={editForm.tattoo_number} onChange={(e) => setEditForm({ ...editForm, tattoo_number: e.target.value })} /></div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}><label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><input type="checkbox" checked={editForm.is_neutered} onChange={(e) => setEditForm({ ...editForm, is_neutered: e.target.checked })} />Sterilise</label></div>
            </div>
            <div className="form-group"><label className="form-label">Notes</label><textarea className="form-textarea" value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} placeholder="Notes sur l'animal..." /></div>
            <button type="submit" className="btn btn-primary">Enregistrer</button>
          </form>
        ) : (
          <>
            <div className="form-row">
              <div><strong>Espece:</strong> {animal.species}</div><div><strong>Race:</strong> {animal.breed || '-'}</div><div><strong>Sexe:</strong> {animal.sex}</div><div><strong>Ne(e) le:</strong> {animal.date_of_birth || '-'}</div>
              <div><strong>Couleur:</strong> {animal.color || '-'}</div><div><strong>Sterilise:</strong> {animal.is_neutered ? 'Oui' : 'Non'}</div><div><strong>Puce:</strong> {animal.microchip_number || '-'}</div><div><strong>Tatouage:</strong> {animal.tattoo_number || '-'}</div>
            </div>
            {animal.notes && <div style={{ marginTop: '12px' }}><strong>Notes:</strong> <span style={{ whiteSpace: 'pre-wrap' }}>{animal.notes}</span></div>}
          </>
        )}
      </div>

      <div className="tabs">
        {['info', 'weight', 'medical'].map(t => (<button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>{t === 'info' ? 'Informations' : t === 'weight' ? 'Courbe de poids' : 'Dossier medical'}</button>))}
      </div>

      {tab === 'weight' && (
        <div className="card">
          <div className="card-header"><h3 className="card-title">Courbe de poids</h3><form onSubmit={addWeight} style={{ display: 'flex', gap: '8px' }}><input type="number" step="0.01" className="form-input" style={{ width: '120px' }} placeholder="Poids (kg)" value={newWeight} onChange={(e) => setNewWeight(e.target.value)} /><button type="submit" className="btn btn-primary btn-sm">Ajouter</button></form></div>
          {weightChartData.length > 0 ? (<ResponsiveContainer width="100%" height={300}><LineChart data={weightChartData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis unit=" kg" /><Tooltip /><Line type="monotone" dataKey="poids" stroke="var(--primary)" strokeWidth={2} dot={{ r: 4 }} /></LineChart></ResponsiveContainer>) : <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucune donnee de poids</p>}
        </div>
      )}

      {tab === 'medical' && (
        <div className="card">
          <div className="card-header"><h3 className="card-title">Historique medical</h3><button className="btn btn-primary btn-sm" onClick={() => setShowRecordForm(!showRecordForm)}>+ Nouveau dossier</button></div>
          {showRecordForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <h4 style={{ marginBottom: '12px' }}>Nouveau dossier medical (SOAP)</h4>
              <form onSubmit={handleRecordSubmit}>
                <div className="form-row">
                  <div className="form-group"><label className="form-label">Type *</label><select className="form-select" value={recordForm.record_type} onChange={(e) => setRecordForm({ ...recordForm, record_type: e.target.value })}>{Object.entries(recordTypeLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
                  <div className="form-group"><label className="form-label">Template</label><select className="form-select" onChange={(e) => applyTemplate(e.target.value)}><option value="">-- Choisir --</option>{templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
                </div>
                <div className="form-group"><label className="form-label">S - Subjectif (Motif / Anamnese)</label><textarea className="form-textarea" value={recordForm.subjective} onChange={(e) => setRecordForm({ ...recordForm, subjective: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">O - Objectif (Examen clinique)</label><textarea className="form-textarea" value={recordForm.objective} onChange={(e) => setRecordForm({ ...recordForm, objective: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">A - Assessment (Diagnostic)</label><textarea className="form-textarea" value={recordForm.assessment} onChange={(e) => setRecordForm({ ...recordForm, assessment: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">P - Plan (Traitement)</label><textarea className="form-textarea" value={recordForm.plan} onChange={(e) => setRecordForm({ ...recordForm, plan: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Traitement a la maison</label><textarea className="form-textarea" value={recordForm.home_treatment} onChange={(e) => setRecordForm({ ...recordForm, home_treatment: e.target.value })} placeholder="Instructions pour le proprietaire: medicaments, posologie, soins..." /></div>
                <div style={{ display: 'flex', gap: '8px' }}><button type="submit" className="btn btn-primary">Enregistrer</button><button type="button" className="btn btn-secondary" onClick={() => setShowRecordForm(false)}>Annuler</button></div>
              </form>
            </div>
          )}
          <div className="timeline">
            {records.map(r => (
              <div key={r.id} className="timeline-item">
                <div className={`timeline-dot ${r.record_type}`} />
                <div className="card" style={{ marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span className={`badge badge-${r.record_type === 'vaccination' ? 'green' : r.record_type === 'surgery' ? 'red' : 'blue'}`}>{recordTypeLabel[r.record_type] || r.record_type}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{new Date(r.created_at).toLocaleDateString('fr-FR')}</span>
                  </div>
                  {r.subjective && <p><strong>Motif:</strong> {r.subjective}</p>}
                  {r.assessment && <p><strong>Diagnostic:</strong> {r.assessment}</p>}
                  {r.plan && <p><strong>Plan:</strong> {r.plan}</p>}
                  {r.home_treatment && (
                    <div style={{ background: 'var(--gray-50)', padding: '8px', borderRadius: '6px', marginTop: '8px' }}>
                      <strong>Traitement a la maison:</strong>
                      <p style={{ whiteSpace: 'pre-wrap', margin: '4px 0' }}>{r.home_treatment}</p>
                      <button className="btn btn-primary btn-sm" onClick={() => sendHomeTreatment(r)} style={{ marginTop: '4px' }}>Envoyer par email</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {records.length === 0 && <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun dossier medical</p>}
          </div>
        </div>
      )}
    </div>
  );
}
