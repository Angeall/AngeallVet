import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { animalsAPI, medicalAPI, hospitalizationAPI, billingAPI, inventoryAPI, communicationsAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

export default function AnimalDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [animal, setAnimal] = useState(null);
  const [weights, setWeights] = useState([]);
  const [records, setRecords] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [hospitalizations, setHospitalizations] = useState([]);
  const [tab, setTab] = useState('medical');
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
  const [shortcuts, setShortcuts] = useState([]);
  const [invoiceLines, setInvoiceLines] = useState([{ description: '', quantity: '1', unit_price: '', vat_rate: '20.00', product_id: null }]);
  const [speciesList, setSpeciesList] = useState([]);
  const [createdInvoices, setCreatedInvoices] = useState({});

  // On-site treatment products
  const [onsiteProducts, setOnsiteProducts] = useState([]);
  const [onsiteProductSearch, setOnsiteProductSearch] = useState('');
  const [onsiteProductResults, setOnsiteProductResults] = useState([]);

  // Home treatment products
  const [htProducts, setHtProducts] = useState([]);
  const [htProductSearch, setHtProductSearch] = useState('');
  const [htProductResults, setHtProductResults] = useState([]);

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
        is_neutered: aRes.data.is_neutered, vital_status: aRes.data.vital_status || 'alive',
        vital_status_date: aRes.data.vital_status_date || '', notes: aRes.data.notes || '',
      });
    } catch { toast.error('Erreur de chargement'); }
  };

  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    animalsAPI.listSpecies().then(res => setSpeciesList(res.data || [])).catch(() => {});
  }, []);

  const loadProducts = async () => {
    try {
      const [pRes, sRes] = await Promise.all([
        inventoryAPI.listProducts({}),
        inventoryAPI.getShortcuts(),
      ]);
      setProducts(pRes.data || []);
      setShortcuts(sRes.data || []);
    } catch {}
  };

  // Debounced search for on-site treatment products
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

  // Debounced search for home treatment products
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
    setHtProductSearch(''); setHtProductResults([]);
  };
  const removeHtProduct = (idx) => setHtProducts(prev => prev.filter((_, i) => i !== idx));
  const updateHtProductQty = (idx, qty) => {
    setHtProducts(prev => { const u = [...prev]; u[idx] = { ...u[idx], quantity: parseFloat(qty) || 1 }; return u; });
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
    if (t) {
      setRecordForm({ ...recordForm, subjective: t.subjective || '', objective: t.objective || '', assessment: t.assessment || '', plan: t.plan || '' });
      if (t.products) {
        setOnsiteProducts(t.products.filter(p => p.treatment_location === 'onsite').map(p => ({ product_id: p.product_id, quantity: parseFloat(p.quantity), product_name: '' })));
        setHtProducts(t.products.filter(p => p.treatment_location === 'home').map(p => ({ product_id: p.product_id, quantity: parseFloat(p.quantity), product_name: '' })));
      }
    }
  };

  const handleRecordSubmit = async (e) => {
    e.preventDefault();
    try {
      await medicalAPI.createRecord({
        ...recordForm, animal_id: parseInt(id),
        onsite_treatment_products: onsiteProducts.map(p => ({ product_id: p.product_id, quantity: p.quantity })),
        home_treatment_products: htProducts.map(p => ({ product_id: p.product_id, quantity: p.quantity })),
      });
      toast.success('Dossier medical cree'); setShowRecordForm(false);
      setRecordForm({ record_type: 'consultation', subjective: '', objective: '', assessment: '', plan: '', home_treatment: '', notes: '' });
      setOnsiteProducts([]); setHtProducts([]);
      const rRes = await medicalAPI.listRecords({ animal_id: id }); setRecords(rRes.data);
    } catch { toast.error('Erreur lors de la creation'); }
  };

  const handleCreateInvoiceFromRecord = async (recordId) => {
    try {
      const res = await medicalAPI.createInvoiceFromRecord(recordId);
      const invoiceId = res.data.id;
      setCreatedInvoices(prev => ({ ...prev, [recordId]: invoiceId }));
      toast.success('Facture brouillon creee');
      navigate(`/invoices/${invoiceId}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors de la creation de la facture');
    }
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
      await animalsAPI.update(id, { ...editForm, date_of_birth: editForm.date_of_birth || null, microchip_number: editForm.microchip_number || null, tattoo_number: editForm.tattoo_number || null, vital_status_date: editForm.vital_status_date || null, is_deceased: editForm.vital_status === 'deceased', notes: editForm.notes || null });
      toast.success('Animal mis a jour'); setShowEditForm(false); load();
    } catch { toast.error('Erreur'); }
  };

  const addInvoiceLine = () => setInvoiceLines([...invoiceLines, { description: '', quantity: '1', unit_price: '', vat_rate: '20.00', product_id: null }]);
  const removeInvoiceLine = (idx) => { if (invoiceLines.length > 1) setInvoiceLines(invoiceLines.filter((_, i) => i !== idx)); };
  const updateInvoiceLine = (idx, field, value) => { const l = [...invoiceLines]; l[idx][field] = value; setInvoiceLines(l); };
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
  const vitalStatusLabels = { alive: 'Vivant', lost: 'Perdu', deceased: 'Decede' };
  const vitalStatusColors = { alive: 'green', lost: 'purple', deceased: 'red' };
  const weightChartData = [...weights].reverse().map(w => ({ date: new Date(w.recorded_at).toLocaleDateString('fr-FR'), poids: parseFloat(w.weight_kg) }));
  const recordTypeLabel = { consultation: 'Consultation', vaccination: 'Vaccination', surgery: 'Chirurgie', lab_result: 'Labo', imaging: 'Imagerie', note: 'Note' };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <nav className="page-breadcrumb">
            <Link to="/animals">Animaux</Link>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{animal.name}</span>
          </nav>
          <h1 className="page-title">{animal.name}</h1>
          <span className={`badge badge-${vitalStatusColors[animal.vital_status] || 'green'}`} style={{ marginLeft: '8px' }}>{vitalStatusLabels[animal.vital_status] || 'Vivant'}</span>
          {animal.client_id && <Link to={`/clients/${animal.client_id}`} className="breadcrumb-link" style={{ marginLeft: '12px' }}>Voir le client</Link>}
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

      {animal.vital_status && animal.vital_status !== 'alive' && (
        <div className={`alert-banner ${animal.vital_status === 'deceased' ? 'danger' : 'warning'}`}>
          {vitalStatusLabels[animal.vital_status] || animal.vital_status}
          {animal.vital_status_date && ` - ${new Date(animal.vital_status_date + 'T00:00').toLocaleDateString('fr-FR')}`}
        </div>
      )}

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
          {shortcuts.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
              {shortcuts.map((s) => (<button key={s.id} type="button" className="btn btn-secondary btn-sm" onClick={() => addProductLine(s)}>{s.name} ({parseFloat(s.selling_price).toFixed(2)} EUR)</button>))}
            </div>
          )}
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

      {/* Alerts - compact */}
      {(animal.alerts?.filter(a => a.is_active).length > 0 || showAlertForm) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
          {animal.alerts?.filter(a => a.is_active).map(alert => (
            <div key={alert.id} className={`alert-banner ${alert.severity}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: 0, padding: '6px 12px', fontSize: '0.85rem' }}>
              <span><strong>{alertTypeLabels[alert.alert_type] || alert.alert_type}:</strong> {alert.message}</span>
              <button className="btn btn-sm" onClick={() => removeAlert(alert.id)} style={{ background: 'rgba(255,255,255,0.3)', border: 'none', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px' }}>X</button>
            </div>
          ))}
          {showAlertForm && (
            <div className="card" style={{ padding: '12px', margin: 0 }}>
              <form onSubmit={handleAlertSubmit}>
                <div className="form-row">
                  <div className="form-group"><label className="form-label">Type *</label><select className="form-select" value={alertForm.alert_type} onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}>{Object.entries(alertTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
                  <div className="form-group"><label className="form-label">Severite</label><select className="form-select" value={alertForm.severity} onChange={(e) => setAlertForm({ ...alertForm, severity: e.target.value })}>{Object.entries(severityLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
                  <div className="form-group" style={{ flex: 2 }}><label className="form-label">Message *</label><input className="form-input" value={alertForm.message} onChange={(e) => setAlertForm({ ...alertForm, message: e.target.value })} required /></div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}><button type="submit" className="btn btn-primary btn-sm">Ajouter</button><button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAlertForm(false)}>Annuler</button></div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Animal info - always visible */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Informations</h3>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowAlertForm(!showAlertForm)}>+ Alerte</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowEditForm(!showEditForm)}>{showEditForm ? 'Annuler' : 'Modifier'}</button>
          </div>
        </div>
        {showEditForm ? (
          <form onSubmit={handleEditSubmit}>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Nom *</label><input className="form-input" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} required /></div>
              <div className="form-group"><label className="form-label">Espece</label><select className="form-select" value={editForm.species} onChange={(e) => setEditForm({ ...editForm, species: e.target.value })}>{speciesList.map(s => <option key={s.code} value={s.code}>{s.label}</option>)}</select></div>
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
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Statut vital</label>
                <select className="form-select" value={editForm.vital_status} onChange={(e) => setEditForm({ ...editForm, vital_status: e.target.value, vital_status_date: e.target.value !== 'alive' ? (editForm.vital_status_date || new Date().toISOString().slice(0, 10)) : '' })}>
                  <option value="alive">Vivant</option>
                  <option value="lost">Perdu</option>
                  <option value="deceased">Decede</option>
                </select>
              </div>
              {editForm.vital_status !== 'alive' && (
                <div className="form-group">
                  <label className="form-label">Date du changement</label>
                  <input type="date" className="form-input" value={editForm.vital_status_date} onChange={(e) => setEditForm({ ...editForm, vital_status_date: e.target.value })} />
                </div>
              )}
            </div>
            <div className="form-group"><label className="form-label">Notes</label><textarea className="form-textarea" value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} placeholder="Notes sur l'animal..." /></div>
            <button type="submit" className="btn btn-primary">Enregistrer</button>
          </form>
        ) : (
          <>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', fontSize: '0.88rem' }}>
              <div><strong>Espece:</strong> {animal.species || '-'}</div>
              <div><strong>Race:</strong> {animal.breed || '-'}</div>
              <div><strong>Sexe:</strong> {animal.sex === 'male' ? 'Male' : animal.sex === 'female' ? 'Femelle' : '-'}</div>
              <div><strong>Ne(e) le:</strong> {animal.date_of_birth ? new Date(animal.date_of_birth + 'T00:00').toLocaleDateString('fr-FR') : '-'}</div>
              <div><strong>Couleur:</strong> {animal.color || '-'}</div>
              <div><strong>Sterilise:</strong> {animal.is_neutered ? 'Oui' : 'Non'}</div>
              <div><strong>Puce:</strong> {animal.microchip_number || '-'}</div>
              <div><strong>Tatouage:</strong> {animal.tattoo_number || '-'}</div>
              <div><strong>Statut:</strong> <span className={`badge badge-${vitalStatusColors[animal.vital_status] || 'green'}`}>{vitalStatusLabels[animal.vital_status] || 'Vivant'}</span>{animal.vital_status_date && ` (${new Date(animal.vital_status_date + 'T00:00').toLocaleDateString('fr-FR')})`}</div>
              <div><strong>Poids:</strong> {weights.length > 0 ? `${parseFloat(weights[0].weight_kg).toFixed(1)} kg` : '-'}</div>
            </div>
            {animal.notes && <div style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--gray-500)' }}><strong>Notes:</strong> <span style={{ whiteSpace: 'pre-wrap' }}>{animal.notes}</span></div>}
          </>
        )}
      </div>

      <div className="tabs">
        {['medical', 'weight'].map(t => (<button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>{t === 'weight' ? 'Courbe de poids' : 'Dossier medical'}</button>))}
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

                {/* P - Sur place */}
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
                </div>
                <div className="form-group"><label className="form-label">Notes supplementaires sur place</label><textarea className="form-textarea" value={recordForm.plan} onChange={(e) => setRecordForm({ ...recordForm, plan: e.target.value })} placeholder="Actes realises en clinique..." /></div>

                {/* A domicile */}
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
                </div>
                <div className="form-group"><label className="form-label">Notes supplementaires domicile</label><textarea className="form-textarea" value={recordForm.home_treatment} onChange={(e) => setRecordForm({ ...recordForm, home_treatment: e.target.value })} placeholder="Instructions pour le proprietaire: medicaments, posologie, soins..." /></div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}><button type="submit" className="btn btn-primary">Enregistrer</button><button type="button" className="btn btn-secondary" onClick={() => setShowRecordForm(false)}>Annuler</button></div>
              </form>
            </div>
          )}
          <div className="timeline">
            {records.map(r => {
              const onsiteProds = (r.home_treatment_products || []).filter(p => p.treatment_location === 'onsite');
              const homeProds = (r.home_treatment_products || []).filter(p => p.treatment_location !== 'onsite');
              const allProds = r.home_treatment_products || [];
              return (
                <div key={r.id} className="timeline-item">
                  <div className={`timeline-dot ${r.record_type}`} />
                  <div className="card" style={{ marginBottom: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span className={`badge badge-${r.record_type === 'vaccination' ? 'green' : r.record_type === 'surgery' ? 'red' : 'blue'}`}>{recordTypeLabel[r.record_type] || r.record_type}</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{new Date(r.created_at).toLocaleDateString('fr-FR')}</span>
                    </div>
                    {r.subjective && <p><strong>Motif:</strong> {r.subjective}</p>}
                    {r.assessment && <p><strong>Diagnostic:</strong> {r.assessment}</p>}
                    {r.plan && <p><strong>Traitement sur place:</strong> {r.plan}</p>}
                    {onsiteProds.length > 0 && (
                      <div style={{ background: 'var(--blue-50, var(--gray-50))', padding: '8px', borderRadius: '6px', marginTop: '4px' }}>
                        <strong style={{ fontSize: '0.85rem' }}>Actes sur place:</strong>
                        {onsiteProds.map((p, i) => <span key={i} className="badge badge-blue" style={{ marginLeft: '6px' }}>{p.product_name || `#${p.product_id}`} x{parseFloat(p.quantity)}</span>)}
                      </div>
                    )}
                    {r.home_treatment && (
                      <div style={{ background: 'var(--gray-50)', padding: '8px', borderRadius: '6px', marginTop: '8px' }}>
                        <strong>Traitement a domicile:</strong>
                        <p style={{ whiteSpace: 'pre-wrap', margin: '4px 0' }}>{r.home_treatment}</p>
                        <button className="btn btn-primary btn-sm" onClick={() => sendHomeTreatment(r)} style={{ marginTop: '4px' }}>Envoyer par email</button>
                      </div>
                    )}
                    {homeProds.length > 0 && (
                      <div style={{ background: 'var(--gray-50)', padding: '8px', borderRadius: '6px', marginTop: '4px' }}>
                        <strong style={{ fontSize: '0.85rem' }}>Medicaments a domicile:</strong>
                        {homeProds.map((p, i) => <span key={i} className="badge badge-amber" style={{ marginLeft: '6px' }}>{p.product_name || `#${p.product_id}`} x{parseFloat(p.quantity)}</span>)}
                      </div>
                    )}
                    {allProds.length > 0 && (
                      createdInvoices[r.id] ? (
                        <Link to={`/invoices/${createdInvoices[r.id]}`} className="btn btn-success btn-sm" style={{ marginTop: '8px', textDecoration: 'none' }}>
                          Facture creee
                        </Link>
                      ) : (
                        <button className="btn btn-secondary btn-sm" onClick={() => handleCreateInvoiceFromRecord(r.id)} style={{ marginTop: '8px' }}>
                          Creer facture ({allProds.length} produit{allProds.length > 1 ? 's' : ''})
                        </button>
                      )
                    )}
                  </div>
                </div>
              );
            })}
            {records.length === 0 && <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun dossier medical</p>}
          </div>
        </div>
      )}
    </div>
  );
}
