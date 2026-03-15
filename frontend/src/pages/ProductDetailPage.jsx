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
  const [showLotForm, setShowLotForm] = useState(false);
  const [lotForm, setLotForm] = useState({ lot_number: '', expiry_date: '', quantity: '' });

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

  const handleLotSubmit = async (e) => {
    e.preventDefault();
    try {
      await inventoryAPI.addLot(id, {
        lot_number: lotForm.lot_number,
        expiry_date: lotForm.expiry_date,
        quantity: parseFloat(lotForm.quantity),
      });
      toast.success('Lot ajoute');
      setShowLotForm(false);
      setLotForm({ lot_number: '', expiry_date: '', quantity: '' });
      const res = await inventoryAPI.getProduct(id);
      setProduct(res.data);
    } catch {
      toast.error('Erreur lors de l\'ajout du lot');
    }
  };

  if (!product) return <div className="page-content">Chargement...</div>;

  const showLots = product.product_type === 'medication' || product.product_type === 'food';

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <nav className="page-breadcrumb">
            <Link to="/inventory">Stocks & Pharmacie</Link>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{product.name}</span>
          </nav>
          <h1 className="page-title">{product.name}</h1>
        </div>
        <div className="page-header-actions" style={{ display: 'flex', gap: '8px' }}>
          <span className={`badge badge-${product.product_type === 'medication' ? 'green' : 'blue'}`}>
            {typeLabels[product.product_type]}
          </span>
          {product.is_controlled_substance && (
            <span className="badge badge-red">Substance controlee</span>
          )}
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

      {showLots && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Lots ({(product.lots || []).length})</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowLotForm(!showLotForm)}>+ Ajouter un lot</button>
          </div>

          {showLotForm && (
            <div style={{ border: '1px solid var(--gray-200)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
              <form onSubmit={handleLotSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">N de lot *</label>
                    <input className="form-input" value={lotForm.lot_number} onChange={(e) => setLotForm({ ...lotForm, lot_number: e.target.value })} required placeholder="Ex: LOT-2025-001" style={{ fontFamily: 'monospace' }} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Date d'expiration *</label>
                    <input type="date" className="form-input" value={lotForm.expiry_date} onChange={(e) => setLotForm({ ...lotForm, expiry_date: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Quantite *</label>
                    <input type="number" step="0.01" className="form-input" value={lotForm.quantity} onChange={(e) => setLotForm({ ...lotForm, quantity: e.target.value })} required />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="submit" className="btn btn-primary">Ajouter</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowLotForm(false)}>Annuler</button>
                </div>
              </form>
            </div>
          )}

          <table>
            <thead><tr><th>N Lot</th><th>Date d'expiration</th><th>Quantite</th><th>Statut</th></tr></thead>
            <tbody>
              {(product.lots || []).map((lot) => {
                const expDate = new Date(lot.expiry_date);
                const now = new Date();
                const daysLeft = Math.ceil((expDate - now) / 86400000);
                const isExpired = daysLeft < 0;
                const isExpiringSoon = !isExpired && daysLeft <= 90;
                return (
                  <tr key={lot.id}>
                    <td style={{ fontFamily: 'monospace' }}>{lot.lot_number}</td>
                    <td style={{ color: isExpired ? 'var(--red, #ef4444)' : isExpiringSoon ? '#f59e0b' : 'inherit', fontWeight: isExpired || isExpiringSoon ? 600 : 400 }}>
                      {lot.expiry_date}
                    </td>
                    <td>{parseFloat(lot.quantity)}</td>
                    <td>
                      {isExpired ? (
                        <span className="badge badge-red">Expire</span>
                      ) : isExpiringSoon ? (
                        <span className="badge badge-amber">Expire dans {daysLeft}j</span>
                      ) : (
                        <span className="badge badge-green">OK</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {(product.lots || []).length === 0 && (
                <tr><td colSpan="4" className="table-empty">Aucun lot enregistre</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
