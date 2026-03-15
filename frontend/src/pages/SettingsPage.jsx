import React, { useState, useEffect, useCallback, useRef } from 'react';
import { settingsAPI, animalsAPI, medicalAPI, inventoryAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const [tab, setTab] = useState('clinic');
  const [clinic, setClinic] = useState({
    clinic_name: '', address: '', city: '', postal_code: '', country: 'France',
    phone: '', email: '', siret: '', ape_code: '', vat_number: '', logo_url: '',
    default_appointment_duration_minutes: 30, debt_acknowledgment_template: '',
  });
  const [vatRates, setVatRates] = useState([]);
  const [vatForm, setVatForm] = useState({ rate: '', label: '', is_default: false });
  const [showVatForm, setShowVatForm] = useState(false);
  const [saving, setSaving] = useState(false);

  // Species state
  const [species, setSpecies] = useState([]);
  const [speciesForm, setSpeciesForm] = useState({ code: '', label: '', display_order: 0 });
  const [editingSpeciesId, setEditingSpeciesId] = useState(null);
  const [showSpeciesForm, setShowSpeciesForm] = useState(false);

  // Templates state
  const [templates, setTemplates] = useState([]);
  const [speciesForTemplates, setSpeciesForTemplates] = useState([]);
  const [templateForm, setTemplateForm] = useState({
    name: '', category: '', species_id: '',
    subjective: '', objective: '', assessment: '', plan: '', home_treatment: '',
    products: [],
  });
  const [editingTemplateId, setEditingTemplateId] = useState(null);
  const [showTemplateForm, setShowTemplateForm] = useState(false);
  const [productSearch, setProductSearch] = useState('');
  const [productResults, setProductResults] = useState([]);
  const [productLocation, setProductLocation] = useState('onsite');
  const searchTimeout = useRef(null);

  // ---- Clinic ----
  const loadClinic = useCallback(async () => {
    try {
      const res = await settingsAPI.getClinic();
      const data = res.data;
      setClinic({
        clinic_name: data.clinic_name || '',
        address: data.address || '',
        city: data.city || '',
        postal_code: data.postal_code || '',
        country: data.country || 'France',
        phone: data.phone || '',
        email: data.email || '',
        siret: data.siret || '',
        ape_code: data.ape_code || '',
        vat_number: data.vat_number || '',
        logo_url: data.logo_url || '',
        default_appointment_duration_minutes: data.default_appointment_duration_minutes || 30,
        debt_acknowledgment_template: data.debt_acknowledgment_template || '',
      });
    } catch {
      toast.error('Erreur de chargement des parametres');
    }
  }, []);

  // ---- VAT ----
  const loadVatRates = useCallback(async () => {
    try {
      const res = await settingsAPI.getVatRates();
      setVatRates(res.data);
    } catch {
      toast.error('Erreur de chargement des taux de TVA');
    }
  }, []);

  // ---- Species ----
  const loadSpecies = useCallback(async () => {
    try {
      const res = await animalsAPI.listSpecies();
      setSpecies(res.data);
    } catch {
      toast.error('Erreur de chargement des especes');
    }
  }, []);

  // ---- Templates ----
  const loadTemplates = useCallback(async () => {
    try {
      const res = await medicalAPI.listTemplates();
      setTemplates(Array.isArray(res.data) ? res.data : res.data.items || []);
    } catch {
      toast.error('Erreur de chargement des templates');
    }
  }, []);

  const loadSpeciesForTemplates = useCallback(async () => {
    try {
      const res = await animalsAPI.listSpecies();
      setSpeciesForTemplates(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadClinic();
    loadVatRates();
  }, [loadClinic, loadVatRates]);

  useEffect(() => {
    if (tab === 'species') loadSpecies();
    if (tab === 'templates') { loadTemplates(); loadSpeciesForTemplates(); }
  }, [tab, loadSpecies, loadTemplates, loadSpeciesForTemplates]);

  // ---- Clinic handlers ----
  const handleClinicSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(clinic).map(([k, v]) => [k, v === '' ? null : v])
      );
      await settingsAPI.updateClinic(payload);
      toast.success('Parametres mis a jour');
    } catch {
      toast.error('Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  // ---- VAT handlers ----
  const handleVatSubmit = async (e) => {
    e.preventDefault();
    try {
      await settingsAPI.createVatRate({
        rate: parseFloat(vatForm.rate),
        label: vatForm.label,
        is_default: vatForm.is_default,
      });
      toast.success('Taux de TVA cree');
      setVatForm({ rate: '', label: '', is_default: false });
      setShowVatForm(false);
      loadVatRates();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  const toggleDefault = async (rate) => {
    try {
      await settingsAPI.updateVatRate(rate.id, { is_default: !rate.is_default });
      loadVatRates();
    } catch {
      toast.error('Erreur');
    }
  };

  const deleteVatRate = async (id) => {
    if (!confirm('Supprimer ce taux de TVA ?')) return;
    try {
      await settingsAPI.deleteVatRate(id);
      toast.success('Taux supprime');
      loadVatRates();
    } catch {
      toast.error('Erreur');
    }
  };

  // ---- Species handlers ----
  const handleSpeciesSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        code: speciesForm.code,
        label: speciesForm.label,
        display_order: parseInt(speciesForm.display_order) || 0,
      };
      if (editingSpeciesId) {
        await animalsAPI.updateSpecies(editingSpeciesId, payload);
        toast.success('Espece mise a jour');
        setEditingSpeciesId(null);
      } else {
        await animalsAPI.createSpecies(payload);
        toast.success('Espece creee');
      }
      setSpeciesForm({ code: '', label: '', display_order: 0 });
      setShowSpeciesForm(false);
      loadSpecies();
    } catch {
      toast.error('Erreur lors de la sauvegarde de l\'espece');
    }
  };

  const editSpecies = (s) => {
    setSpeciesForm({ code: s.code || '', label: s.label || '', display_order: s.display_order || 0 });
    setEditingSpeciesId(s.id);
    setShowSpeciesForm(true);
  };

  const deleteSpecies = async (id) => {
    if (!confirm('Supprimer cette espece ?')) return;
    try {
      await animalsAPI.deleteSpecies(id);
      toast.success('Espece supprimee');
      loadSpecies();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  const cancelSpeciesEdit = () => {
    setSpeciesForm({ code: '', label: '', display_order: 0 });
    setEditingSpeciesId(null);
    setShowSpeciesForm(false);
  };

  // ---- Template handlers ----
  const resetTemplateForm = () => {
    setTemplateForm({
      name: '', category: '', species_id: '',
      subjective: '', objective: '', assessment: '', plan: '', home_treatment: '',
      products: [],
    });
    setEditingTemplateId(null);
    setShowTemplateForm(false);
    setProductSearch('');
    setProductResults([]);
  };

  const handleTemplateSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: templateForm.name,
        category: templateForm.category || null,
        species_id: templateForm.species_id ? parseInt(templateForm.species_id) : null,
        subjective: templateForm.subjective || null,
        objective: templateForm.objective || null,
        assessment: templateForm.assessment || null,
        plan: templateForm.plan || null,
        home_treatment: templateForm.home_treatment || null,
        products: templateForm.products.map((p) => ({
          product_id: p.product_id,
          quantity: parseFloat(p.quantity) || 1,
          treatment_location: p.treatment_location,
        })),
      };
      if (editingTemplateId) {
        await medicalAPI.updateTemplate(editingTemplateId, payload);
        toast.success('Template mis a jour');
      } else {
        await medicalAPI.createTemplate(payload);
        toast.success('Template cree');
      }
      resetTemplateForm();
      loadTemplates();
    } catch {
      toast.error('Erreur lors de la sauvegarde du template');
    }
  };

  const editTemplate = async (t) => {
    try {
      const res = await medicalAPI.getTemplate(t.id);
      const data = res.data;
      setTemplateForm({
        name: data.name || '',
        category: data.category || '',
        species_id: data.species_id ? String(data.species_id) : '',
        subjective: data.subjective || '',
        objective: data.objective || '',
        assessment: data.assessment || '',
        plan: data.plan || '',
        home_treatment: data.home_treatment || '',
        products: (data.products || []).map((p) => ({
          product_id: p.product_id,
          product_name: p.product_name || p.name || `Produit #${p.product_id}`,
          quantity: p.quantity || 1,
          treatment_location: p.treatment_location || 'onsite',
        })),
      });
      setEditingTemplateId(t.id);
      setShowTemplateForm(true);
    } catch {
      toast.error('Erreur lors du chargement du template');
    }
  };

  const deleteTemplate = async (id) => {
    if (!confirm('Supprimer ce template ?')) return;
    try {
      await medicalAPI.deleteTemplate(id);
      toast.success('Template supprime');
      loadTemplates();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  // Product search with debounce
  const handleProductSearch = (value) => {
    setProductSearch(value);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (value.length < 2) { setProductResults([]); return; }
    searchTimeout.current = setTimeout(async () => {
      try {
        const res = await inventoryAPI.listProducts({ search: value });
        const items = Array.isArray(res.data) ? res.data : res.data.items || [];
        setProductResults(items);
      } catch {
        setProductResults([]);
      }
    }, 300);
  };

  const addProductToTemplate = (product) => {
    const exists = templateForm.products.find(
      (p) => p.product_id === product.id && p.treatment_location === productLocation
    );
    if (exists) {
      toast.error('Ce produit est deja ajoute pour cet emplacement');
      return;
    }
    setTemplateForm({
      ...templateForm,
      products: [
        ...templateForm.products,
        {
          product_id: product.id,
          product_name: product.name,
          quantity: 1,
          treatment_location: productLocation,
        },
      ],
    });
    setProductSearch('');
    setProductResults([]);
  };

  const updateProductQuantity = (index, quantity) => {
    const updated = [...templateForm.products];
    updated[index] = { ...updated[index], quantity: parseFloat(quantity) || 1 };
    setTemplateForm({ ...templateForm, products: updated });
  };

  const removeProduct = (index) => {
    const updated = templateForm.products.filter((_, i) => i !== index);
    setTemplateForm({ ...templateForm, products: updated });
  };

  const getSpeciesLabel = (speciesId) => {
    const s = speciesForTemplates.find((sp) => sp.id === speciesId);
    return s ? s.label : '-';
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Parametres</h1>
          <p className="page-subtitle">Configuration du cabinet veterinaire</p>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'clinic' ? 'tab active' : 'tab'} onClick={() => setTab('clinic')}>
          Informations du cabinet
        </button>
        <button className={tab === 'vat' ? 'tab active' : 'tab'} onClick={() => setTab('vat')}>
          Taux de TVA
        </button>
        <button className={tab === 'species' ? 'tab active' : 'tab'} onClick={() => setTab('species')}>
          Especes
        </button>
        <button className={tab === 'templates' ? 'tab active' : 'tab'} onClick={() => setTab('templates')}>
          Templates SOAP
        </button>
      </div>

      {/* ---- CLINIC TAB ---- */}
      {tab === 'clinic' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Informations du cabinet</h3>
          </div>
          <form onSubmit={handleClinicSubmit}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Nom du cabinet</label>
                <input className="form-input" value={clinic.clinic_name} onChange={(e) => setClinic({ ...clinic, clinic_name: e.target.value })} placeholder="Clinique Veterinaire AngeallVet" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Adresse</label>
                <input className="form-input" value={clinic.address} onChange={(e) => setClinic({ ...clinic, address: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Code postal</label>
                <input className="form-input" value={clinic.postal_code} onChange={(e) => setClinic({ ...clinic, postal_code: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Ville</label>
                <input className="form-input" value={clinic.city} onChange={(e) => setClinic({ ...clinic, city: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Telephone</label>
                <input className="form-input" value={clinic.phone} onChange={(e) => setClinic({ ...clinic, phone: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input type="email" className="form-input" value={clinic.email} onChange={(e) => setClinic({ ...clinic, email: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">SIRET</label>
                <input className="form-input" value={clinic.siret} onChange={(e) => setClinic({ ...clinic, siret: e.target.value })} placeholder="12345678901234" />
              </div>
              <div className="form-group">
                <label className="form-label">Code APE</label>
                <input className="form-input" value={clinic.ape_code} onChange={(e) => setClinic({ ...clinic, ape_code: e.target.value })} placeholder="7500Z" />
              </div>
              <div className="form-group">
                <label className="form-label">N TVA intracommunautaire</label>
                <input className="form-input" value={clinic.vat_number} onChange={(e) => setClinic({ ...clinic, vat_number: e.target.value })} placeholder="FR12345678901" />
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--gray-200)', margin: '20px 0', paddingTop: '20px' }}>
              <h4 style={{ marginBottom: '12px' }}>Rendez-vous</h4>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Duree par defaut (minutes)</label>
                  <input type="number" className="form-input" value={clinic.default_appointment_duration_minutes} onChange={(e) => setClinic({ ...clinic, default_appointment_duration_minutes: parseInt(e.target.value) || 30 })} min="5" max="480" step="5" />
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Enregistrement...' : 'Enregistrer'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ---- VAT TAB ---- */}
      {tab === 'vat' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Taux de TVA</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowVatForm(!showVatForm)}>
              + Nouveau taux
            </button>
          </div>

          {showVatForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleVatSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Taux (%)</label>
                    <input type="number" className="form-input" step="0.01" value={vatForm.rate} onChange={(e) => setVatForm({ ...vatForm, rate: e.target.value })} required placeholder="20.00" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Libelle</label>
                    <input className="form-input" value={vatForm.label} onChange={(e) => setVatForm({ ...vatForm, label: e.target.value })} required placeholder="TVA 20%" />
                  </div>
                  <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input type="checkbox" checked={vatForm.is_default} onChange={(e) => setVatForm({ ...vatForm, is_default: e.target.checked })} />
                      Par defaut
                    </label>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Creer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowVatForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Taux</th>
                  <th>Libelle</th>
                  <th>Par defaut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {vatRates.map((rate) => (
                  <tr key={rate.id}>
                    <td style={{ fontWeight: 600 }}>{parseFloat(rate.rate).toFixed(2)}%</td>
                    <td>{rate.label}</td>
                    <td>
                      <button
                        className={`badge ${rate.is_default ? 'badge-green' : 'badge-gray'}`}
                        style={{ cursor: 'pointer', border: 'none' }}
                        onClick={() => toggleDefault(rate)}
                        title={rate.is_default ? 'Taux par defaut' : 'Definir comme defaut'}
                      >
                        {rate.is_default ? 'Par defaut' : '-'}
                      </button>
                    </td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => deleteVatRate(rate.id)} style={{ color: 'var(--danger)' }}>
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
                {vatRates.length === 0 && (
                  <tr><td colSpan="4" className="table-empty">
                    Aucun taux de TVA configure. Cliquez sur "+ Nouveau taux" pour commencer.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---- SPECIES TAB ---- */}
      {tab === 'species' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Especes</h3>
            <button className="btn btn-primary btn-sm" onClick={() => { setShowSpeciesForm(!showSpeciesForm); if (showSpeciesForm) cancelSpeciesEdit(); }}>
              {showSpeciesForm ? 'Fermer' : '+ Nouvelle espece'}
            </button>
          </div>

          {showSpeciesForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleSpeciesSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Code</label>
                    <input className="form-input" value={speciesForm.code} onChange={(e) => setSpeciesForm({ ...speciesForm, code: e.target.value })} required placeholder="DOG" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Libelle</label>
                    <input className="form-input" value={speciesForm.label} onChange={(e) => setSpeciesForm({ ...speciesForm, label: e.target.value })} required placeholder="Chien" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Ordre d'affichage</label>
                    <input type="number" className="form-input" value={speciesForm.display_order} onChange={(e) => setSpeciesForm({ ...speciesForm, display_order: e.target.value })} placeholder="0" />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">
                    {editingSpeciesId ? 'Mettre a jour' : 'Creer'}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={cancelSpeciesEdit}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Libelle</th>
                  <th>Ordre</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {species.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: 600 }}>{s.code}</td>
                    <td>{s.label}</td>
                    <td>{s.display_order ?? '-'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => editSpecies(s)}>
                          Modifier
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => deleteSpecies(s.id)} style={{ color: 'var(--danger)' }}>
                          Supprimer
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {species.length === 0 && (
                  <tr><td colSpan="4" className="table-empty">
                    Aucune espece configuree. Cliquez sur "+ Nouvelle espece" pour commencer.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---- TEMPLATES SOAP TAB ---- */}
      {tab === 'templates' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Templates SOAP</h3>
            <button className="btn btn-primary btn-sm" onClick={() => { if (showTemplateForm) resetTemplateForm(); else setShowTemplateForm(true); }}>
              {showTemplateForm ? 'Fermer' : '+ Nouveau template'}
            </button>
          </div>

          {showTemplateForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleTemplateSubmit}>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 2 }}>
                    <label className="form-label">Nom *</label>
                    <input className="form-input" value={templateForm.name} onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })} required placeholder="Consultation de routine" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Categorie</label>
                    <input className="form-input" value={templateForm.category} onChange={(e) => setTemplateForm({ ...templateForm, category: e.target.value })} placeholder="Consultation" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Espece</label>
                    <select className="form-select" value={templateForm.species_id} onChange={(e) => setTemplateForm({ ...templateForm, species_id: e.target.value })}>
                      <option value="">Toutes les especes</option>
                      {speciesForTemplates.map((s) => (
                        <option key={s.id} value={s.id}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">Subjectif (S)</label>
                    <textarea className="form-input" rows={3} value={templateForm.subjective} onChange={(e) => setTemplateForm({ ...templateForm, subjective: e.target.value })} placeholder="Motif de consultation, historique..." />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">Objectif (O)</label>
                    <textarea className="form-input" rows={3} value={templateForm.objective} onChange={(e) => setTemplateForm({ ...templateForm, objective: e.target.value })} placeholder="Examen clinique, observations..." />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">Analyse (A)</label>
                    <textarea className="form-input" rows={3} value={templateForm.assessment} onChange={(e) => setTemplateForm({ ...templateForm, assessment: e.target.value })} placeholder="Diagnostic, hypotheses..." />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">Plan (P)</label>
                    <textarea className="form-input" rows={3} value={templateForm.plan} onChange={(e) => setTemplateForm({ ...templateForm, plan: e.target.value })} placeholder="Traitement, suivi..." />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Traitement a domicile</label>
                    <textarea className="form-input" rows={3} value={templateForm.home_treatment} onChange={(e) => setTemplateForm({ ...templateForm, home_treatment: e.target.value })} placeholder="Instructions pour le proprietaire..." />
                  </div>
                </div>

                {/* Product section */}
                <div style={{ borderTop: '1px solid var(--gray-200)', margin: '20px 0', paddingTop: '20px' }}>
                  <h4 style={{ marginBottom: '12px' }}>Produits</h4>

                  <div className="form-row">
                    <div className="form-group" style={{ flex: 2, position: 'relative' }}>
                      <label className="form-label">Rechercher un produit</label>
                      <input className="form-input" value={productSearch} onChange={(e) => handleProductSearch(e.target.value)} placeholder="Tapez pour rechercher..." />
                      {productResults.length > 0 && (
                        <div style={{
                          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                          background: 'white', border: '1px solid var(--gray-200)', borderRadius: '8px',
                          maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                        }}>
                          {productResults.map((p) => (
                            <div key={p.id} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                              onClick={() => addProductToTemplate(p)}
                              onMouseOver={(e) => e.currentTarget.style.background = 'var(--gray-50)'}
                              onMouseOut={(e) => e.currentTarget.style.background = 'white'}
                            >
                              {p.name}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="form-group">
                      <label className="form-label">Emplacement</label>
                      <select className="form-select" value={productLocation} onChange={(e) => setProductLocation(e.target.value)}>
                        <option value="onsite">Sur place</option>
                        <option value="home">A domicile</option>
                      </select>
                    </div>
                  </div>

                  {templateForm.products.length > 0 && (
                    <div className="table-container">
                      <table>
                        <thead>
                          <tr>
                            <th>Produit</th>
                            <th>Quantite</th>
                            <th>Emplacement</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {templateForm.products.map((p, index) => (
                            <tr key={`${p.product_id}-${p.treatment_location}-${index}`}>
                              <td>{p.product_name}</td>
                              <td>
                                <input type="number" className="form-input" style={{ width: '80px' }} min="0.01" step="0.01" value={p.quantity} onChange={(e) => updateProductQuantity(index, e.target.value)} />
                              </td>
                              <td>
                                <span className={`badge ${p.treatment_location === 'onsite' ? 'badge-blue' : 'badge-orange'}`}>
                                  {p.treatment_location === 'onsite' ? 'Sur place' : 'A domicile'}
                                </span>
                              </td>
                              <td>
                                <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeProduct(index)} style={{ color: 'var(--danger)' }}>
                                  Retirer
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">
                    {editingTemplateId ? 'Mettre a jour' : 'Creer'}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={resetTemplateForm}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Categorie</th>
                  <th>Espece</th>
                  <th>Produits</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((t) => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 600 }}>{t.name}</td>
                    <td>{t.category || '-'}</td>
                    <td>{t.species_id ? getSpeciesLabel(t.species_id) : 'Toutes'}</td>
                    <td>{t.products?.length ?? 0}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => editTemplate(t)}>
                          Modifier
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => deleteTemplate(t.id)} style={{ color: 'var(--danger)' }}>
                          Supprimer
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {templates.length === 0 && (
                  <tr><td colSpan="5" className="table-empty">
                    Aucun template configure. Cliquez sur "+ Nouveau template" pour commencer.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
