import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { inventoryAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function InventoryPage() {
  const [products, setProducts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '', product_type: 'medication', selling_price: '', purchase_price: '',
    vat_rate: '20.00', unit: '', stock_alert_threshold: '5', ean13: '',
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

  const toggleShortcut = async (product) => {
    try {
      await inventoryAPI.updateProduct(product.id, { is_shortcut: !product.is_shortcut });
      setProducts(products.map(p => p.id === product.id ? { ...p, is_shortcut: !p.is_shortcut } : p));
    } catch { toast.error('Erreur'); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await inventoryAPI.createProduct({
        ...form,
        selling_price: parseFloat(form.selling_price),
        purchase_price: form.purchase_price ? parseFloat(form.purchase_price) : null,
        vat_rate: parseFloat(form.vat_rate),
        stock_alert_threshold: parseFloat(form.stock_alert_threshold),
        ean13: form.ean13 || null,
      });
      toast.success('Produit cree');
      setShowForm(false);
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const typeLabels = { medication: 'Medicament', food: 'Alimentation', supply: 'Fourniture', service: 'Acte medical' };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Stocks & Pharmacie</h1>
          <span className="page-subtitle">{products.length} produit(s)</span>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouveau produit</button>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="alert-banner warning" style={{ marginBottom: '16px' }}>
          ! {alerts.length} produit(s) en stock bas
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
                <label className="form-label">Unite</label>
                <input className="form-input" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="comprime, ml, kg..." />
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
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Code EAN13</label>
                <input className="form-input" value={form.ean13} onChange={(e) => setForm({ ...form, ean13: e.target.value })} placeholder="13 chiffres" maxLength={13} style={{ fontFamily: 'monospace' }} />
              </div>
              <div className="form-group">
                <label className="form-label">Seuil alerte stock</label>
                <input type="number" className="form-input" value={form.stock_alert_threshold} onChange={(e) => setForm({ ...form, stock_alert_threshold: e.target.value })} />
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
                <th>Reference</th>
                <th>Nom</th>
                <th>Type</th>
                <th>EAN13</th>
                <th>Prix vente</th>
                <th>TVA</th>
                <th>Stock</th>
                <th>Seuil</th>
                <th style={{ textAlign: 'center' }}>Raccourci</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.reference}</td>
                  <td style={{ fontWeight: 500 }}>
                    <Link to={`/inventory/${p.id}`} className="table-link">{p.name}</Link>
                  </td>
                  <td><span className="badge badge-blue">{typeLabels[p.product_type]}</span></td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{p.ean13 || '-'}</td>
                  <td>{parseFloat(p.selling_price).toFixed(2)} EUR</td>
                  <td>{parseFloat(p.vat_rate).toFixed(0)}%</td>
                  <td>
                    {p.product_type === 'service' ? (
                      <span className="badge badge-blue">&#8734;</span>
                    ) : (
                      <span className={`badge ${parseFloat(p.stock_quantity) <= parseFloat(p.stock_alert_threshold) ? 'badge-red' : 'badge-green'}`}>
                        {parseFloat(p.stock_quantity)} {p.unit || ''}
                      </span>
                    )}
                  </td>
                  <td>{p.product_type === 'service' ? '-' : parseFloat(p.stock_alert_threshold)}</td>
                  <td style={{ textAlign: 'center' }}>
                    <input type="checkbox" checked={!!p.is_shortcut} onChange={() => toggleShortcut(p)} title="Afficher comme raccourci facturation" />
                  </td>
                </tr>
              ))}
              {products.length === 0 && (
                <tr><td colSpan="9" className="table-empty">Aucun produit trouve</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
