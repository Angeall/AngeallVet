import React, { useState, useEffect } from 'react';
import { clientsAPI, inventoryAPI, billingAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function SalesPage() {
  const [products, setProducts] = useState([]);
  const [lines, setLines] = useState([]);

  // Client search
  const [clientSearch, setClientSearch] = useState('');
  const [clientResults, setClientResults] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);

  useEffect(() => {
    inventoryAPI.listProducts({ limit: 500 }).then(res => setProducts(res.data || [])).catch(() => {});
  }, []);

  // Client search with debounce
  useEffect(() => {
    if (clientSearch.length < 2) { setClientResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await clientsAPI.list({ search: clientSearch });
        setClientResults(res.data || []);
      } catch {}
    }, 300);
    return () => clearTimeout(timer);
  }, [clientSearch]);

  const selectClient = (client) => {
    setSelectedClient(client);
    setClientSearch(`${client.last_name} ${client.first_name}`);
    setClientResults([]);
  };

  const addProduct = (product) => {
    const existing = lines.findIndex(l => l.product_id === product.id);
    if (existing >= 0) {
      const updated = [...lines];
      updated[existing].quantity += 1;
      setLines(updated);
    } else {
      setLines([...lines, {
        product_id: product.id,
        description: product.name,
        quantity: 1,
        unit_price: parseFloat(product.selling_price || 0),
        vat_rate: parseFloat(product.vat_rate || 20),
      }]);
    }
  };

  const updateLine = (idx, field, value) => {
    const updated = [...lines];
    updated[idx] = { ...updated[idx], [field]: value };
    setLines(updated);
  };

  const removeLine = (idx) => {
    setLines(lines.filter((_, i) => i !== idx));
  };

  const total = lines.reduce((sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0);
  const totalTTC = lines.reduce((sum, l) => {
    const ht = (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0);
    return sum + ht * (1 + (parseFloat(l.vat_rate) || 0) / 100);
  }, 0);

  const submitSale = async () => {
    if (!selectedClient) { toast.error('Selectionnez un client'); return; }
    if (lines.length === 0) { toast.error('Ajoutez au moins un produit'); return; }
    try {
      await billingAPI.createInvoice({
        client_id: selectedClient.id,
        animal_id: null,
        status: 'paid',
        lines: lines.map(l => ({
          description: l.description,
          quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price),
          vat_rate: parseFloat(l.vat_rate),
        })),
      });
      toast.success('Vente enregistree');
      setLines([]);
      setSelectedClient(null);
      setClientSearch('');
    } catch {
      toast.error('Erreur lors de l\'enregistrement');
    }
  };

  const [productFilter, setProductFilter] = useState('');
  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(productFilter.toLowerCase()) ||
    (p.ean13 && p.ean13.includes(productFilter))
  );

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Vente comptoir</h1>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Left: Product catalog */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '12px' }}>Produits</h3>
          <input
            className="form-input"
            placeholder="Rechercher par nom ou code-barres..."
            value={productFilter}
            onChange={(e) => setProductFilter(e.target.value)}
            style={{ marginBottom: '12px' }}
          />
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {filteredProducts.slice(0, 50).map(p => (
              <div key={p.id} onClick={() => addProduct(p)} style={{
                padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--gray-50)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
              >
                <div>
                  <strong>{p.name}</strong>
                  {p.ean13 && <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.8rem' }}>{p.ean13}</span>}
                </div>
                <span style={{ fontWeight: 600 }}>{parseFloat(p.selling_price || 0).toFixed(2)} EUR</span>
              </div>
            ))}
            {filteredProducts.length === 0 && (
              <p style={{ color: 'var(--gray-400)', textAlign: 'center', padding: '16px' }}>Aucun produit trouve</p>
            )}
          </div>
        </div>

        {/* Right: Cart */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '12px' }}>Panier</h3>

          {/* Client search */}
          <div className="form-group" style={{ position: 'relative', marginBottom: '12px' }}>
            <label className="form-label">Client *</label>
            <input
              className="form-input"
              placeholder="Rechercher un client..."
              value={clientSearch}
              onChange={(e) => { setClientSearch(e.target.value); setSelectedClient(null); }}
            />
            {clientResults.length > 0 && !selectedClient && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                {clientResults.map(c => (
                  <div key={c.id} onClick={() => selectClient(c)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                    onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                    onMouseLeave={(e) => e.target.style.background = 'white'}>
                    <strong>{c.last_name} {c.first_name}</strong>
                    <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{c.phone || c.email || ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {lines.length > 0 ? (
            <>
              <table style={{ marginBottom: '12px' }}>
                <thead><tr><th>Produit</th><th>Qte</th><th>Prix</th><th>Total</th><th></th></tr></thead>
                <tbody>
                  {lines.map((line, idx) => (
                    <tr key={idx}>
                      <td>{line.description}</td>
                      <td>
                        <input type="number" className="form-input" value={line.quantity}
                          onChange={(e) => updateLine(idx, 'quantity', e.target.value)}
                          style={{ width: '60px' }} min="1" />
                      </td>
                      <td>{parseFloat(line.unit_price).toFixed(2)}</td>
                      <td style={{ fontWeight: 600 }}>
                        {((parseFloat(line.quantity) || 0) * (parseFloat(line.unit_price) || 0)).toFixed(2)}
                      </td>
                      <td>
                        <button className="btn btn-secondary btn-sm" onClick={() => removeLine(idx)} style={{ color: 'red' }}>X</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div style={{ borderTop: '2px solid var(--gray-200)', paddingTop: '12px', marginBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span>Total HT:</span>
                  <strong>{total.toFixed(2)} EUR</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.1rem' }}>
                  <span>Total TTC:</span>
                  <strong style={{ color: 'var(--primary)' }}>{totalTTC.toFixed(2)} EUR</strong>
                </div>
              </div>

              <button className="btn btn-primary" style={{ width: '100%' }} onClick={submitSale}>
                Encaisser {totalTTC.toFixed(2)} EUR
              </button>
            </>
          ) : (
            <p style={{ color: 'var(--gray-400)', textAlign: 'center', padding: '32px 0' }}>
              Cliquez sur un produit pour l'ajouter au panier
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
