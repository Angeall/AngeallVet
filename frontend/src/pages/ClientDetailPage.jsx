import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clientsAPI, animalsAPI, billingAPI, communicationsAPI, inventoryAPI } from '../services/api';
import toast from 'react-hot-toast';

const defaultPrices = [
  { label: 'Consultation', price: 40, vat: 20 },
  { label: 'Vaccination', price: 55, vat: 20 },
  { label: 'Detartrage', price: 120, vat: 20 },
  { label: 'Sterilisation chien', price: 250, vat: 20 },
  { label: 'Sterilisation chat', price: 150, vat: 20 },
  { label: 'Analyse sanguine', price: 65, vat: 20 },
  { label: 'Radiographie', price: 80, vat: 20 },
  { label: 'Echographie', price: 90, vat: 20 },
];

export default function ClientDetailPage() {
  const { id } = useParams();
  const [client, setClient] = useState(null);
  const [animals, setAnimals] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [comms, setComms] = useState([]);
  const [tab, setTab] = useState('animals');
  const [showAnimalForm, setShowAnimalForm] = useState(false);
  const [animalForm, setAnimalForm] = useState({
    name: '', species: 'dog', breed: '', sex: 'male',
    date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false,
  });

  // Quick invoice state
  const [showInvoiceForm, setShowInvoiceForm] = useState(false);
  const [invoiceLines, setInvoiceLines] = useState([]);
  const [invoiceAnimalId, setInvoiceAnimalId] = useState('');
  const [products, setProducts] = useState([]);

  // Client alerts state
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [alertForm, setAlertForm] = useState({ alert_type: 'bad_payer', message: '', severity: 'warning' });

  // Client notes state
  const [notes, setNotes] = useState([]);
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [noteContent, setNoteContent] = useState('');

  // Edit client modal state
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editLoading, setEditLoading] = useState(false);

  const load = async () => {
    try {
      const [cRes, aRes, iRes, commRes, notesRes] = await Promise.all([
        clientsAPI.get(id),
        animalsAPI.list({ client_id: id }),
        billingAPI.listInvoices({ client_id: id }),
        communicationsAPI.list({ client_id: id }),
        clientsAPI.listNotes(id),
      ]);
      setClient(cRes.data);
      setAnimals(aRes.data);
      setInvoices(iRes.data);
      setComms(commRes.data);
      setNotes(notesRes.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    if (showInvoiceForm && products.length === 0) {
      inventoryAPI.listProducts({ limit: 200 }).then(res => setProducts(res.data || [])).catch(() => {});
    }
  }, [showInvoiceForm]);

  const handleAnimalSubmit = async (e) => {
    e.preventDefault();
    try {
      await animalsAPI.create({
        ...animalForm,
        client_id: parseInt(id),
        date_of_birth: animalForm.date_of_birth || null,
        microchip_number: animalForm.microchip_number || null,
        tattoo_number: animalForm.tattoo_number || null,
      });
      toast.success('Animal cree');
      setShowAnimalForm(false);
      setAnimalForm({ name: '', species: 'dog', breed: '', sex: 'male', date_of_birth: '', color: '', microchip_number: '', tattoo_number: '', is_neutered: false });
      load();
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  const addDefaultLine = (item) => {
    setInvoiceLines([...invoiceLines, { description: item.label, quantity: 1, unit_price: item.price, vat_rate: item.vat }]);
  };

  const addProductLine = (product) => {
    setInvoiceLines([...invoiceLines, {
      description: product.name, quantity: 1,
      unit_price: parseFloat(product.selling_price || 0), vat_rate: parseFloat(product.vat_rate || 20),
    }]);
  };

  const removeInvoiceLine = (idx) => {
    setInvoiceLines(invoiceLines.filter((_, i) => i !== idx));
  };

  const updateInvoiceLine = (idx, field, value) => {
    const updated = [...invoiceLines];
    updated[idx] = { ...updated[idx], [field]: value };
    setInvoiceLines(updated);
  };

  const openEditModal = () => {
    setEditForm({
      first_name: client?.first_name || '',
      last_name: client?.last_name || '',
      email: client?.email || '',
      phone: client?.phone || '',
      mobile: client?.mobile || '',
      address: client?.address || '',
      postal_code: client?.postal_code || '',
      city: client?.city || '',
      country: client?.country || 'France',
      notes: client?.notes || '',
      vat_number: client?.vat_number || '',
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setEditLoading(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(editForm).map(([k, v]) => [k, v === '' ? null : v])
      );
      await clientsAPI.update(id, payload);
      toast.success('Client mis a jour');
      setShowEditModal(false);
      load();
    } catch {
      toast.error('Erreur lors de la mise a jour');
    } finally {
      setEditLoading(false);
    }
  };

  const clientAlertTypeLabels = { bad_payer: 'Mauvais payeur', aggressive: 'Agressif', blacklisted: 'Liste noire', other: 'Autre' };
  const severityLabels = { info: 'Info', warning: 'Attention', danger: 'Danger' };

  const handleAlertSubmit = async (e) => {
    e.preventDefault();
    try {
      await clientsAPI.addAlert(id, alertForm);
      toast.success('Alerte ajoutee');
      setShowAlertForm(false);
      setAlertForm({ alert_type: 'bad_payer', message: '', severity: 'warning' });
      load();
    } catch { toast.error('Erreur'); }
  };

  const removeAlert = async (alertId) => {
    try { await clientsAPI.removeAlert(id, alertId); toast.success('Alerte supprimee'); load(); } catch { toast.error('Erreur'); }
  };

  const handleNoteSubmit = async (e) => {
    e.preventDefault();
    if (!noteContent.trim()) return;
    try {
      await clientsAPI.addNote(id, { content: noteContent });
      toast.success('Note ajoutee');
      setNoteContent('');
      setShowNoteForm(false);
      load();
    } catch { toast.error('Erreur'); }
  };

  const deleteNote = async (noteId) => {
    try { await clientsAPI.deleteNote(id, noteId); toast.success('Note supprimee'); load(); } catch { toast.error('Erreur'); }
  };

  const invoiceTotal = invoiceLines.reduce((sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0);

  const submitInvoice = async () => {
    if (invoiceLines.length === 0) { toast.error('Ajoutez au moins une ligne'); return; }
    try {
      await billingAPI.createInvoice({
        client_id: parseInt(id),
        animal_id: invoiceAnimalId ? parseInt(invoiceAnimalId) : null,
        lines: invoiceLines.map(l => ({
          description: l.description, quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price), vat_rate: parseFloat(l.vat_rate),
        })),
      });
      toast.success('Facture creee');
      setShowInvoiceForm(false);
      setInvoiceLines([]);
      setInvoiceAnimalId('');
      load();
    } catch { toast.error('Erreur lors de la creation'); }
  };

  if (!client) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <nav className="page-breadcrumb">
            <Link to="/clients">Clients</Link>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{client.last_name} {client.first_name}</span>
          </nav>
          <h1 className="page-title">{client.last_name} {client.first_name}</h1>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-secondary" onClick={openEditModal} title="Modifier le client">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            {' '}Modifier
          </button>
          <button className="btn btn-primary" onClick={() => { setShowInvoiceForm(!showInvoiceForm); setTab('invoices'); }}>
            + Facturation rapide
          </button>
        </div>
      </div>

      {(() => {
        const warnings = [];
        if (!client.email) warnings.push('Adresse email manquante');
        if (!client.phone && !client.mobile) warnings.push('Aucun numero de telephone');
        if (!client.address) warnings.push('Adresse postale manquante');
        if (warnings.length === 0) return null;
        return (
          <div className="alert-banner warning" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              <span>Fiche incomplete : {warnings.join(' — ')}</span>
            </div>
            <button className="btn btn-sm" style={{ background: 'rgba(146,64,14,0.15)', color: '#92400e', border: '1px solid #fcd34d', whiteSpace: 'nowrap' }} onClick={openEditModal}>
              Completer
            </button>
          </div>
        );
      })()}

      {(() => {
        const fosterAnimals = animals.filter(a => a.association_name);
        if (fosterAnimals.length === 0) return null;
        const assocNames = [...new Set(fosterAnimals.map(a => a.association_name))];
        return (
          <div className="alert-banner" style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#f3e8ff', border: '1px solid #d8b4fe', borderRadius: '8px', padding: '10px 16px', marginBottom: '16px' }}>
            <span style={{ fontSize: '1.2rem' }}>&#x1f3e0;</span>
            <span style={{ color: '#7c3aed', fontWeight: 500 }}>
              Famille d'accueil : {assocNames.join(', ')}
            </span>
          </div>
        );
      })()}

      {/* Client Alerts */}
      {((client.alerts?.filter(a => a.is_active).length > 0) || showAlertForm) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
          {client.alerts?.filter(a => a.is_active).map(alert => (
            <div key={alert.id} className={`alert-banner ${alert.severity}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: 0, padding: '6px 12px', fontSize: '0.85rem' }}>
              <span><strong>{clientAlertTypeLabels[alert.alert_type] || alert.alert_type}:</strong> {alert.message}</span>
              <button className="btn btn-sm" onClick={() => removeAlert(alert.id)} style={{ background: 'rgba(255,255,255,0.3)', border: 'none', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px' }}>X</button>
            </div>
          ))}
          {showAlertForm && (
            <div className="card" style={{ padding: '12px', margin: 0 }}>
              <form onSubmit={handleAlertSubmit}>
                <div className="form-row">
                  <div className="form-group"><label className="form-label">Type *</label><select className="form-select" value={alertForm.alert_type} onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}>{Object.entries(clientAlertTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
                  <div className="form-group"><label className="form-label">Severite</label><select className="form-select" value={alertForm.severity} onChange={(e) => setAlertForm({ ...alertForm, severity: e.target.value })}>{Object.entries(severityLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
                  <div className="form-group" style={{ flex: 2 }}><label className="form-label">Message *</label><input className="form-input" value={alertForm.message} onChange={(e) => setAlertForm({ ...alertForm, message: e.target.value })} required /></div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}><button type="submit" className="btn btn-primary btn-sm">Ajouter</button><button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAlertForm(false)}>Annuler</button></div>
              </form>
            </div>
          )}
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">P</div>
          <div><div className="stat-value">{animals.length}</div><div className="stat-label">Animaux</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">F</div>
          <div><div className="stat-value">{invoices.length}</div><div className="stat-label">Factures</div></div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${parseFloat(client.account_balance) < 0 ? 'red' : 'green'}`}>EUR</div>
          <div>
            <div className="stat-value">{parseFloat(client.account_balance || 0).toFixed(2)}</div>
            <div className="stat-label">Solde (EUR)</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 className="card-title">Coordonnees</h3>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowAlertForm(!showAlertForm)}>+ Alerte</button>
            <button className="btn btn-secondary btn-sm" onClick={openEditModal} title="Modifier">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
          </div>
        </div>
        <div className="form-row" style={{ marginTop: '12px' }}>
          <div><strong>Email:</strong> {client.email || '-'}</div>
          <div><strong>Tel:</strong> {client.phone || '-'}</div>
          <div><strong>Mobile:</strong> {client.mobile || '-'}</div>
        </div>
        <div style={{ marginTop: '8px' }}>
          <strong>Adresse:</strong> {client.address} {client.postal_code} {client.city}
        </div>
        {client.vat_number && (
          <div style={{ marginTop: '8px' }}>
            <strong>N TVA:</strong> {client.vat_number}
          </div>
        )}
      </div>

      <div className="tabs">
        {['animals', 'notes', 'invoices', 'communications'].map((t) => (
          <button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>
            {t === 'animals' ? 'Animaux' : t === 'notes' ? `Notes (${notes.length})` : t === 'invoices' ? 'Factures' : 'Communications'}
          </button>
        ))}
      </div>

      {tab === 'animals' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Animaux</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAnimalForm(!showAnimalForm)}>+ Nouvel animal</button>
          </div>

          {showAnimalForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleAnimalSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Nom *</label>
                    <input className="form-input" value={animalForm.name} onChange={(e) => setAnimalForm({ ...animalForm, name: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Espece *</label>
                    <select className="form-select" value={animalForm.species} onChange={(e) => setAnimalForm({ ...animalForm, species: e.target.value })}>
                      <option value="dog">Chien</option>
                      <option value="cat">Chat</option>
                      <option value="bird">Oiseau</option>
                      <option value="rabbit">Lapin</option>
                      <option value="reptile">Reptile</option>
                      <option value="horse">Cheval</option>
                      <option value="nac">NAC</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Race</label>
                    <input className="form-input" value={animalForm.breed} onChange={(e) => setAnimalForm({ ...animalForm, breed: e.target.value })} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Sexe</label>
                    <select className="form-select" value={animalForm.sex} onChange={(e) => setAnimalForm({ ...animalForm, sex: e.target.value })}>
                      <option value="male">Male</option>
                      <option value="female">Femelle</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Date de naissance</label>
                    <input type="date" className="form-input" value={animalForm.date_of_birth} onChange={(e) => setAnimalForm({ ...animalForm, date_of_birth: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Couleur</label>
                    <input className="form-input" value={animalForm.color} onChange={(e) => setAnimalForm({ ...animalForm, color: e.target.value })} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">N Puce</label>
                    <input className="form-input" value={animalForm.microchip_number} onChange={(e) => setAnimalForm({ ...animalForm, microchip_number: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">N Tatouage</label>
                    <input className="form-input" value={animalForm.tattoo_number} onChange={(e) => setAnimalForm({ ...animalForm, tattoo_number: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input type="checkbox" checked={animalForm.is_neutered} onChange={(e) => setAnimalForm({ ...animalForm, is_neutered: e.target.checked })} />
                      Sterilise
                    </label>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Enregistrer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowAnimalForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <table>
            <thead><tr><th>Nom</th><th>Espece</th><th>Race</th><th>Sexe</th><th>Puce</th><th>Association</th></tr></thead>
            <tbody>
              {animals.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/animals/${a.id}`} className="table-link">{a.name}</Link></td>
                  <td>{a.species}</td>
                  <td>{a.breed || '-'}</td>
                  <td>{a.sex}</td>
                  <td>{a.microchip_number || '-'}</td>
                  <td>{a.association_name ? <span className="badge badge-purple">{a.association_name}</span> : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'notes' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Notes</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowNoteForm(!showNoteForm)}>+ Nouvelle note</button>
          </div>
          {showNoteForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleNoteSubmit}>
                <div className="form-group">
                  <label className="form-label">Contenu de la note *</label>
                  <textarea className="form-textarea" rows={4} value={noteContent} onChange={(e) => setNoteContent(e.target.value)} placeholder="Ecrire une note sur ce client..." required />
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Enregistrer</button>
                  <button type="button" className="btn btn-secondary" onClick={() => { setShowNoteForm(false); setNoteContent(''); }}>Annuler</button>
                </div>
              </form>
            </div>
          )}
          <div className="timeline">
            {notes.map(n => (
              <div key={n.id} className="timeline-item">
                <div className="timeline-dot note" />
                <div className="card" style={{ marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span className="badge badge-blue">Note</span>
                      {n.source === 'appointment' && <span className="badge badge-amber">Prise de RDV</span>}
                      {n.created_by_name && <span style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>{n.created_by_name}</span>}
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{new Date(n.created_at).toLocaleDateString('fr-FR')} {new Date(n.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
                      <button className="btn btn-secondary btn-sm" onClick={() => deleteNote(n.id)} style={{ color: 'var(--danger)', padding: '2px 8px' }}>X</button>
                    </div>
                  </div>
                  <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{n.content}</p>
                </div>
              </div>
            ))}
            {notes.length === 0 && <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucune note pour ce client</p>}
          </div>
        </div>
      )}

      {tab === 'invoices' && (
        <div className="card">
          {showInvoiceForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <h4 style={{ marginBottom: '12px' }}>Facturation rapide</h4>

              <div className="form-group" style={{ marginBottom: '12px' }}>
                <label className="form-label">Animal (optionnel)</label>
                <select className="form-select" value={invoiceAnimalId} onChange={(e) => setInvoiceAnimalId(e.target.value)}>
                  <option value="">-- Aucun --</option>
                  {animals.map(a => <option key={a.id} value={a.id}>{a.name} ({a.species})</option>)}
                </select>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                {defaultPrices.map((item, i) => (
                  <button key={i} type="button" className="btn btn-secondary btn-sm" onClick={() => addDefaultLine(item)}>
                    {item.label} ({item.price} EUR)
                  </button>
                ))}
              </div>

              {products.length > 0 && (
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label className="form-label">Ajouter un produit</label>
                  <select className="form-select" value="" onChange={(e) => {
                    const p = products.find(p => p.id === parseInt(e.target.value));
                    if (p) addProductLine(p);
                  }}>
                    <option value="">-- Choisir un produit --</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name} ({parseFloat(p.selling_price || 0).toFixed(2)} EUR)</option>)}
                  </select>
                </div>
              )}

              {invoiceLines.length > 0 && (
                <table style={{ marginBottom: '12px' }}>
                  <thead><tr><th>Description</th><th>Qte</th><th>Prix HT</th><th>TVA %</th><th>Total</th><th></th></tr></thead>
                  <tbody>
                    {invoiceLines.map((line, idx) => (
                      <tr key={idx}>
                        <td><input className="form-input" value={line.description} onChange={(e) => updateInvoiceLine(idx, 'description', e.target.value)} style={{ minWidth: '150px' }} /></td>
                        <td><input type="number" className="form-input" value={line.quantity} onChange={(e) => updateInvoiceLine(idx, 'quantity', e.target.value)} style={{ width: '60px' }} min="1" /></td>
                        <td><input type="number" className="form-input" value={line.unit_price} onChange={(e) => updateInvoiceLine(idx, 'unit_price', e.target.value)} style={{ width: '80px' }} step="0.01" /></td>
                        <td><input type="number" className="form-input" value={line.vat_rate} onChange={(e) => updateInvoiceLine(idx, 'vat_rate', e.target.value)} style={{ width: '60px' }} /></td>
                        <td style={{ fontWeight: 600 }}>{((parseFloat(line.quantity) || 0) * (parseFloat(line.unit_price) || 0)).toFixed(2)}</td>
                        <td><button className="btn btn-secondary btn-sm" onClick={() => removeInvoiceLine(idx)} style={{ color: 'red' }}>X</button></td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr><td colSpan="4" style={{ textAlign: 'right', fontWeight: 700 }}>Total HT:</td><td style={{ fontWeight: 700 }}>{invoiceTotal.toFixed(2)} EUR</td><td></td></tr>
                  </tfoot>
                </table>
              )}

              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary" onClick={submitInvoice}>Creer la facture</button>
                <button className="btn btn-secondary" onClick={() => { setShowInvoiceForm(false); setInvoiceLines([]); }}>Annuler</button>
              </div>
            </div>
          )}

          <table>
            <thead><tr><th>N</th><th>Date</th><th>Total</th><th>Statut</th></tr></thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td><Link to={`/invoices/${inv.id}`} className="table-link">{inv.invoice_number}</Link></td>
                  <td>{inv.issue_date}</td>
                  <td>{parseFloat(inv.total).toFixed(2)} EUR</td>
                  <td><span className={`badge badge-${inv.status === 'paid' ? 'green' : inv.status === 'overdue' ? 'red' : 'amber'}`}>{inv.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'communications' && (
        <div className="card">
          <table>
            <thead><tr><th>Date</th><th>Canal</th><th>Sujet</th><th>Statut</th></tr></thead>
            <tbody>
              {comms.map((c) => (
                <tr key={c.id}>
                  <td>{new Date(c.created_at).toLocaleDateString('fr-FR')}</td>
                  <td><span className="badge badge-blue">{c.channel}</span></td>
                  <td>{c.subject || '-'}</td>
                  <td><span className={`badge badge-${c.status === 'sent' ? 'green' : 'amber'}`}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showEditModal && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowEditModal(false); }}>
          <div className="modal">
            <div className="modal-header">
              <h2 className="modal-title">Modifier le client</h2>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <form onSubmit={handleEditSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Prenom *</label>
                  <input className="form-input" value={editForm.first_name} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Nom *</label>
                  <input className="form-input" value={editForm.last_name} onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })} required />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input type="email" className="form-input" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Telephone</label>
                  <input className="form-input" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Mobile</label>
                  <input className="form-input" value={editForm.mobile} onChange={(e) => setEditForm({ ...editForm, mobile: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group" style={{ flex: 2 }}>
                  <label className="form-label">Adresse</label>
                  <input className="form-input" value={editForm.address} onChange={(e) => setEditForm({ ...editForm, address: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Code postal</label>
                  <input className="form-input" value={editForm.postal_code} onChange={(e) => setEditForm({ ...editForm, postal_code: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Ville</label>
                  <input className="form-input" value={editForm.city} onChange={(e) => setEditForm({ ...editForm, city: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Pays</label>
                  <input className="form-input" value={editForm.country} onChange={(e) => setEditForm({ ...editForm, country: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">N TVA (entreprises)</label>
                  <input className="form-input" placeholder="FR12345678901" value={editForm.vat_number} onChange={(e) => setEditForm({ ...editForm, vat_number: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Notes</label>
                <textarea className="form-textarea" rows={3} value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary" disabled={editLoading}>
                  {editLoading ? 'Enregistrement...' : 'Enregistrer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
