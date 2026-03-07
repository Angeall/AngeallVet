import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { inventoryAPI } from '../services/api';
import toast from 'react-hot-toast';

const typeLabels = { medication: 'Medicament', food: 'Alimentation', supply: 'Fourniture', service: 'Acte medical' };

export default function ProductDetailPage() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ ean13: '', notes: '' });

  useEffect(() => {
    async function load() {
      try {
        const res = await inventoryAPI.getProduct(id);
        setProduct(res.data);
        setForm({ ean13: res.data.ean13 || '', notes: res.data.notes || '' });
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, [id]);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      const res = await inventoryAPI.updateProduct(id, {
        ean13: form.ean13 || null,
        notes: form.notes || null,
      });
      setProduct(res.data);
      setEditing(false);
      toast.success('Produit mis a jour');
    } catch {
      toast.error('Erreur');
    }
  };

  if (!product) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/inventory" className="breadcrumb-link">Stocks & Pharmacie /</Link>
          <h1 className="page-title">{product.name}</h1>
        </div>
        <div className="page-header-actions">
          <span className={`badge badge-${product.product_type === 'medication' ? 'green' : 'blue'}`}>
            {typeLabels[product.product_type]}
          </span>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">REF</div>
          <div><div className="stat-value" style={{ fontSize: '0.9rem', fontFamily: 'monospace' }}>{product.reference}</div><div className="stat-label">Reference</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">EUR</div>
          <div><div className="stat-value">{parseFloat(product.selling_price).toFixed(2)}</div><div className="stat-label">Prix de vente HT</div></div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${parseFloat(product.stock_quantity) <= parseFloat(product.stock_alert_threshold) ? 'red' : 'green'}`}>
            STK
          </div>
          <div><div className="stat-value">{parseFloat(product.stock_quantity)} {product.unit || ''}</div><div className="stat-label">Stock</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">TVA</div>
          <div><div className="stat-value">{parseFloat(product.vat_rate).toFixed(0)}%</div><div className="stat-label">TVA</div></div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Informations</h3>
        <div className="form-row">
          <div><strong>Type:</strong> {typeLabels[product.product_type]}</div>
          <div><strong>Unite:</strong> {product.unit || '-'}</div>
          <div><strong>Prix d'achat HT:</strong> {product.purchase_price ? parseFloat(product.purchase_price).toFixed(2) + ' EUR' : '-'}</div>
          <div><strong>Seuil d'alerte:</strong> {parseFloat(product.stock_alert_threshold)}</div>
          <div><strong>Ordonnance requise:</strong> {product.requires_prescription ? 'Oui' : 'Non'}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">EAN13 & Notes veterinaires</h3>
          {!editing && (
            <button className="btn btn-primary btn-sm" onClick={() => setEditing(true)}>Modifier</button>
          )}
        </div>

        {editing ? (
          <form onSubmit={handleSave}>
            <div className="form-group">
              <label className="form-label">Code EAN13</label>
              <input
                className="form-input"
                value={form.ean13}
                onChange={(e) => setForm({ ...form, ean13: e.target.value })}
                placeholder="Ex: 3401560055016"
                maxLength={13}
                pattern="[0-9]{13}"
                title="13 chiffres"
                style={{ fontFamily: 'monospace', maxWidth: '250px' }}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Notes veterinaires</label>
              <textarea
                className="form-textarea"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Posologie, contre-indications, remarques..."
                rows={6}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Enregistrer</button>
              <button type="button" className="btn btn-secondary" onClick={() => { setEditing(false); setForm({ ean13: product.ean13 || '', notes: product.notes || '' }); }}>Annuler</button>
            </div>
          </form>
        ) : (
          <div>
            <div style={{ marginBottom: '12px' }}>
              <strong>EAN13:</strong>{' '}
              <span style={{ fontFamily: 'monospace' }}>{product.ean13 || '-'}</span>
            </div>
            <div>
              <strong>Notes:</strong>
              <p style={{ whiteSpace: 'pre-wrap', marginTop: '4px', color: product.notes ? 'inherit' : 'var(--gray-400)' }}>
                {product.notes || 'Aucune note'}
              </p>
            </div>
          </div>
        )}
      </div>

      {product.lots && product.lots.length > 0 && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Lots</h3>
          <table>
            <thead><tr><th>N° Lot</th><th>Date d'expiration</th><th>Quantite</th></tr></thead>
            <tbody>
              {product.lots.map((lot) => (
                <tr key={lot.id}>
                  <td style={{ fontFamily: 'monospace' }}>{lot.lot_number}</td>
                  <td>{lot.expiry_date}</td>
                  <td>{parseFloat(lot.quantity)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
