import React, { useState, useEffect, useCallback } from 'react';
import { inventoryAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function InventoryPage() {
  const [products, setProducts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState('products');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '', product_type: 'medication', selling_price: '', purchase_price: '',
    vat_rate: '20.00', unit: '', stock_alert_threshold: '5',
  });

  const load = useCallback(async () => {
    try {
      const [pRes, aRes] = await Promise.all([
        inventoryAPI.listProducts({ search: search || undefined }),
        inventoryAPI.getAlerts(),
      ]);
      setProducts(pRes.data);
      setAlerts(aRes.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await inventoryAPI.createProduct({
        ...form,
        selling_price: parseFloat(form.selling_price),
        purchase_price: form.purchase_price ? parseFloat(form.purchase_price) : null,
        vat_rate: parseFloat(form.vat_rate),
        stock_alert_threshold: parseFloat(form.stock_alert_threshold),
      });
      toast.success('Produit créé');
      setShowForm(false);
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const typeLabels = { medication: 'Médicament', food: 'Alimentation', supply: 'Fourniture', service: 'Acte médical' };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Stocks & Pharmacie</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouveau produit</button>
      </div>

      {alerts.length > 0 && (
        <div className="alert-banner warning" style={{ marginBottom: '16px' }}>
          ⚡ {alerts.length} produit(s) en stock bas
        </div>
      )}

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau produit</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Nom *</label>
                <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Type *</label>
                <select className="form-select" value={form.product_type} onChange={(e) => setForm({ ...form, product_type: e.target.value })}>
                  {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Unité</label>
                <input className="form-input" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="comprimé, ml, kg..." />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Prix d'achat HT</label>
                <input type="number" step="0.01" className="form-input" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Prix de vente HT *</label>
                <input type="number" step="0.01" className="form-input" value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">TVA %</label>
                <input type="number" step="0.01" className="form-input" value={form.vat_rate} onChange={(e) => setForm({ ...form, vat_rate: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ marginBottom: '16px' }}>
          <input className="form-input" placeholder="Rechercher un produit..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Référence</th>
                <th>Nom</th>
                <th>Type</th>
                <th>Prix vente</th>
                <th>TVA</th>
                <th>Stock</th>
                <th>Seuil</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.reference}</td>
                  <td style={{ fontWeight: 500 }}>{p.name}</td>
                  <td><span className="badge badge-blue">{typeLabels[p.product_type]}</span></td>
                  <td>{parseFloat(p.selling_price).toFixed(2)} EUR</td>
                  <td>{parseFloat(p.vat_rate).toFixed(0)}%</td>
                  <td>
                    <span className={`badge ${parseFloat(p.stock_quantity) <= parseFloat(p.stock_alert_threshold) ? 'badge-red' : 'badge-green'}`}>
                      {parseFloat(p.stock_quantity)} {p.unit || ''}
                    </span>
                  </td>
                  <td>{parseFloat(p.stock_alert_threshold)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
