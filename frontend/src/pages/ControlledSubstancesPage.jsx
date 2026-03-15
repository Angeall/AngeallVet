import React, { useState, useEffect, useCallback } from 'react';
import { controlledSubstancesAPI, inventoryAPI, authAPI, animalsAPI } from '../services/api';
import toast from 'react-hot-toast';

const movementLabels = { in: 'Entree', out: 'Sortie', destruction: 'Destruction', prescription: 'Prescription' };
const movementColors = { in: 'green', out: 'blue', destruction: 'red', prescription: 'amber' };

export default function ControlledSubstancesPage() {
  const [entries, setEntries] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [products, setProducts] = useState([]);
  const [staff, setStaff] = useState([]);
  const [productSearch, setProductSearch] = useState('');
  const [productResults, setProductResults] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [animalSearch, setAnimalSearch] = useState('');
  const [animalResults, setAnimalResults] = useState([]);
  const [selectedAnimal, setSelectedAnimal] = useState(null);
  const [filterProductId, setFilterProductId] = useState('');

  const [form, setForm] = useState({
    product_id: '', date: new Date().toISOString().split('T')[0],
    movement_type: 'in', quantity: '', lot_number: '',
    patient_owner_name: '', patient_animal_id: '', prescribing_vet_id: '', reason: '', notes: '',
    dosage: '', total_delivered: '',
  });

  const load = useCallback(async () => {
    try {
      const params = {};
      if (filterProductId) params.product_id = parseInt(filterProductId);
      const res = await controlledSubstancesAPI.listRegister(params);
      setEntries(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  }, [filterProductId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    async function loadStaff() {
      try {
        const res = await authAPI.listStaff();
        setStaff(res.data || []);
      } catch {}
    }
    loadStaff();
  }, []);

  // Product search for form
  useEffect(() => {
    if (productSearch.length < 2) { setProductResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await inventoryAPI.listProducts({ search: productSearch });
        setProductResults((res.data || []).filter(p => p.is_controlled_substance));
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [productSearch]);

  // Animal search for form
  useEffect(() => {
    if (animalSearch.length < 2) { setAnimalResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await animalsAPI.list({ search: animalSearch });
        setAnimalResults(res.data || []);
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [animalSearch]);

  // Load controlled products for filter
  useEffect(() => {
    async function loadProducts() {
      try {
        const res = await inventoryAPI.listProducts({});
        setProducts((res.data || []).filter(p => p.is_controlled_substance));
      } catch {}
    }
    loadProducts();
  }, []);

  const selectProduct = (product) => {
    setSelectedProduct(product);
    setForm(prev => ({ ...prev, product_id: product.id }));
    setProductSearch(product.name);
    setProductResults([]);
  };

  const selectAnimal = (animal) => {
    setSelectedAnimal(animal);
    setForm(prev => ({ ...prev, patient_animal_id: animal.id, patient_owner_name: '' }));
    setAnimalSearch(animal.name);
    setAnimalResults([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await controlledSubstancesAPI.createEntry({
        product_id: parseInt(form.product_id),
        date: form.date || null,
        movement_type: form.movement_type,
        quantity: parseFloat(form.quantity),
        lot_number: form.lot_number || null,
        patient_owner_name: form.patient_owner_name || null,
        patient_animal_id: form.patient_animal_id ? parseInt(form.patient_animal_id) : null,
        prescribing_vet_id: form.prescribing_vet_id ? parseInt(form.prescribing_vet_id) : null,
        reason: form.reason || null,
        notes: form.notes || null,
        dosage: form.dosage || null,
        total_delivered: form.total_delivered ? parseFloat(form.total_delivered) : null,
      });
      toast.success('Entree ajoutee au registre');
      setShowForm(false);
      setSelectedProduct(null);
      setProductSearch('');
      setSelectedAnimal(null);
      setAnimalSearch('');
      setForm({
        product_id: '', date: new Date().toISOString().split('T')[0],
        movement_type: 'in', quantity: '', lot_number: '',
        patient_owner_name: '', patient_animal_id: '', prescribing_vet_id: '', reason: '', notes: '',
        dosage: '', total_delivered: '',
      });
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const handleExport = async () => {
    try {
      const params = {};
      if (filterProductId) params.product_id = parseInt(filterProductId);
      const res = await controlledSubstancesAPI.exportRegister(params);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'registre_stupefiants.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Erreur lors de l\'export');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Registre des stupefiants</h1>
          <span className="page-subtitle">{entries.length} entree(s)</span>
        </div>
        <div className="page-header-actions" style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={handleExport}>Exporter CSV</button>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouvelle entree</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouvelle entree</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group" style={{ position: 'relative' }}>
                <label className="form-label">Produit *</label>
                <input
                  className="form-input"
                  placeholder="Rechercher une substance controlee..."
                  value={productSearch}
                  onChange={(e) => { setProductSearch(e.target.value); setSelectedProduct(null); setForm(prev => ({ ...prev, product_id: '' })); }}
                  required={!selectedProduct}
                />
                {productResults.length > 0 && !selectedProduct && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                    {productResults.map(p => (
                      <div key={p.id} onMouseDown={() => selectProduct(p)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                        onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                        onMouseLeave={(e) => e.target.style.background = 'white'}>
                        <strong>{p.name}</strong>
                        <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{p.reference}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="form-group">
                <label className="form-label">Type *</label>
                <select className="form-select" value={form.movement_type} onChange={(e) => setForm({ ...form, movement_type: e.target.value })}>
                  {Object.entries(movementLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Date *</label>
                <input type="date" className="form-input" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Quantite *</label>
                <input type="number" step="0.01" className="form-input" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">N de lot</label>
                <input className="form-input" value={form.lot_number} onChange={(e) => setForm({ ...form, lot_number: e.target.value })} style={{ fontFamily: 'monospace' }} />
              </div>
              <div className="form-group" style={{ position: 'relative' }}>
                <label className="form-label">Animal</label>
                <input
                  className="form-input"
                  placeholder="Rechercher un animal..."
                  value={animalSearch}
                  onChange={(e) => { setAnimalSearch(e.target.value); setSelectedAnimal(null); setForm(prev => ({ ...prev, patient_animal_id: '' })); }}
                />
                {animalResults.length > 0 && !selectedAnimal && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                    {animalResults.map(a => (
                      <div key={a.id} onMouseDown={() => selectAnimal(a)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                        onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                        onMouseLeave={(e) => e.target.style.background = 'white'}>
                        <strong>{a.name}</strong>
                        <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{a.species} {a.breed ? `- ${a.breed}` : ''}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Nom du proprietaire</label>
                <input className="form-input" value={form.patient_owner_name} onChange={(e) => setForm({ ...form, patient_owner_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Dosage</label>
                <input className="form-input" value={form.dosage} onChange={(e) => setForm({ ...form, dosage: e.target.value })} placeholder="Ex: 0.5 mg/kg" />
              </div>
              <div className="form-group">
                <label className="form-label">Dose totale delivree</label>
                <input type="number" step="0.01" className="form-input" value={form.total_delivered} onChange={(e) => setForm({ ...form, total_delivered: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Veterinaire prescripteur</label>
                <select className="form-select" value={form.prescribing_vet_id} onChange={(e) => setForm({ ...form, prescribing_vet_id: e.target.value })}>
                  <option value="">-- Moi-meme --</option>
                  {staff.map(s => <option key={s.id} value={s.id}>{s.first_name} {s.last_name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label className="form-label">Motif</label>
                <input className="form-input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder="Traitement, prescription, destruction..." />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Notes</label>
              <textarea className="form-textarea" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <select className="form-select" value={filterProductId} onChange={(e) => setFilterProductId(e.target.value)} style={{ maxWidth: '300px' }}>
            <option value="">Tous les produits</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Produit</th>
                <th>Type</th>
                <th>Quantite</th>
                <th>N Lot</th>
                <th>Animal</th>
                <th>Client</th>
                <th>Dosage</th>
                <th>Dose totale</th>
                <th>Proprietaire</th>
                <th>Veterinaire</th>
                <th>Motif</th>
                <th>Stock restant</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.date}</td>
                  <td style={{ fontWeight: 500 }}>{e.product_name || `#${e.product_id}`}</td>
                  <td>
                    <span className={`badge badge-${movementColors[e.movement_type] || 'gray'}`}>
                      {movementLabels[e.movement_type] || e.movement_type}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {e.movement_type === 'in' ? '+' : '-'}{parseFloat(e.quantity)}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{e.lot_number || '-'}</td>
                  <td>{e.patient_animal_name || '-'}</td>
                  <td>{e.patient_client_name || '-'}</td>
                  <td>{e.dosage || '-'}</td>
                  <td>{e.total_delivered ? parseFloat(e.total_delivered) : '-'}</td>
                  <td>{e.patient_owner_name || '-'}</td>
                  <td>{e.prescribing_vet_name || '-'}</td>
                  <td>{e.reason || '-'}</td>
                  <td style={{ fontWeight: 600 }}>{parseFloat(e.remaining_stock)}</td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr><td colSpan="13" className="table-empty">Aucune entree dans le registre</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
