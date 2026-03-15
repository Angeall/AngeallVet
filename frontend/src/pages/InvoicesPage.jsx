import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { billingAPI, clientsAPI, animalsAPI, inventoryAPI, settingsAPI } from '../services/api';
import toast from 'react-hot-toast';

const statusLabels = {
  draft: 'Brouillon', sent: 'Envoyee', paid: 'Payee',
  partial: 'Partielle', overdue: 'Impayee', cancelled: 'Annulee',
};
const statusColors = {
  draft: 'gray', sent: 'blue', paid: 'green',
  partial: 'amber', overdue: 'red', cancelled: 'gray',
};

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [defaultVatRate, setDefaultVatRate] = useState('20.00');
  const [form, setForm] = useState({
    client_id: '', animal_id: '', lines: [{ description: '', quantity: '1', unit_price: '', vat_rate: '20.00', product_id: null }],
  });

  // Filters
  const [filterSearch, setFilterSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Client search (form)
  const [clientSearch, setClientSearch] = useState('');
  const [clientResults, setClientResults] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [animalOptions, setAnimalOptions] = useState([]);

  // Product search per line
  const [productSearches, setProductSearches] = useState({});
  const [productResults, setProductResults] = useState({});

  const loadInvoices = useCallback(async (params = {}) => {
    try {
      const res = await billingAPI.listInvoices(params);
      setInvoices(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  }, []);

  useEffect(() => {
    loadInvoices({});
    async function loadDefaultVat() {
      try {
        const res = await settingsAPI.getVatRates();
        const def = (res.data || []).find(r => r.is_default);
        if (def) setDefaultVatRate(parseFloat(def.rate).toFixed(2));
      } catch {}
    }
    loadDefaultVat();
  }, [loadInvoices]);

  // Debounced filter
  useEffect(() => {
    const timer = setTimeout(() => {
      const params = {};
      if (filterSearch) params.search = filterSearch;
      if (filterStatus) params.status = filterStatus;
      loadInvoices(params);
    }, 300);
    return () => clearTimeout(timer);
  }, [filterSearch, filterStatus, loadInvoices]);

  // Client search debounce
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

  const selectClient = async (client) => {
    setSelectedClient(client);
    setForm(prev => ({ ...prev, client_id: client.id }));
    setClientSearch(`${client.last_name} ${client.first_name}`);
    setClientResults([]);
    try {
      const res = await animalsAPI.list({ client_id: client.id });
      setAnimalOptions(res.data || []);
    } catch {}
  };

  // Product search debounce per line index
  useEffect(() => {
    const timers = {};
    Object.entries(productSearches).forEach(([idx, query]) => {
      if (!query || query.length < 2) {
        setProductResults(prev => ({ ...prev, [idx]: [] }));
        return;
      }
      timers[idx] = setTimeout(async () => {
        try {
          const res = await inventoryAPI.listProducts({ search: query });
          setProductResults(prev => ({ ...prev, [idx]: res.data || [] }));
        } catch {}
      }, 300);
    });
    return () => Object.values(timers).forEach(clearTimeout);
  }, [productSearches]);

  const selectProduct = (idx, product) => {
    const lines = [...form.lines];
    lines[idx] = {
      ...lines[idx],
      description: product.name,
      unit_price: parseFloat(product.selling_price || 0).toFixed(2),
      vat_rate: product.vat_rate != null ? parseFloat(product.vat_rate).toFixed(2) : defaultVatRate,
      product_id: product.id,
    };
    setForm({ ...form, lines });
    setProductSearches(prev => ({ ...prev, [idx]: '' }));
    setProductResults(prev => ({ ...prev, [idx]: [] }));
  };

  const addLine = () => {
    setForm({ ...form, lines: [...form.lines, { description: '', quantity: '1', unit_price: '', vat_rate: defaultVatRate, product_id: null }] });
  };

  const removeLine = (idx) => {
    if (form.lines.length <= 1) return;
    const lines = form.lines.filter((_, i) => i !== idx);
    setForm({ ...form, lines });
    setProductSearches(prev => { const n = { ...prev }; delete n[idx]; return n; });
    setProductResults(prev => { const n = { ...prev }; delete n[idx]; return n; });
  };

  const updateLine = (idx, field, value) => {
    const lines = [...form.lines];
    lines[idx][field] = value;
    setForm({ ...form, lines });
  };

  const lineTotal = (line) => {
    const qty = parseFloat(line.quantity) || 0;
    const price = parseFloat(line.unit_price) || 0;
    return (qty * price).toFixed(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await billingAPI.createInvoice({
        client_id: parseInt(form.client_id),
        animal_id: form.animal_id ? parseInt(form.animal_id) : null,
        lines: form.lines.map((l) => ({
          description: l.description,
          quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price),
          vat_rate: parseFloat(l.vat_rate),
        })),
      });
      toast.success('Facture creee');
      setShowForm(false);
      setSelectedClient(null);
      setClientSearch('');
      setAnimalOptions([]);
      setForm({ client_id: '', animal_id: '', lines: [{ description: '', quantity: '1', unit_price: '', vat_rate: defaultVatRate, product_id: null }] });
      loadInvoices({});
    } catch {
      toast.error('Erreur lors de la creation');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Factures</h1>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouvelle facture</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouvelle facture</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group" style={{ position: 'relative' }}>
                <label className="form-label">Client *</label>
                <input
                  className="form-input"
                  placeholder="Rechercher un client..."
                  value={clientSearch}
                  onChange={(e) => { setClientSearch(e.target.value); setSelectedClient(null); setForm(prev => ({ ...prev, client_id: '', animal_id: '' })); setAnimalOptions([]); }}
                  required={!selectedClient}
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
              <div className="form-group">
                <label className="form-label">Animal</label>
                <select className="form-select" value={form.animal_id} onChange={(e) => setForm({ ...form, animal_id: e.target.value })}>
                  <option value="">-- Choisir --</option>
                  {animalOptions.map(a => <option key={a.id} value={a.id}>{a.name} ({a.species})</option>)}
                </select>
              </div>
            </div>
            <h4 style={{ marginBottom: '8px' }}>Lignes de facture</h4>
            {form.lines.map((line, idx) => (
              <div className="line-item-row" key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', marginBottom: '8px' }}>
                <div className="form-group" style={{ flex: 1, position: 'relative' }}>
                  {idx === 0 && <label className="form-label">Description / Produit</label>}
                  <input
                    className="form-input"
                    placeholder="Rechercher un produit ou saisir..."
                    value={productSearches[idx] !== undefined && productSearches[idx] !== '' ? productSearches[idx] : line.description}
                    onChange={(e) => {
                      const val = e.target.value;
                      setProductSearches(prev => ({ ...prev, [idx]: val }));
                      updateLine(idx, 'description', val);
                    }}
                    onFocus={() => { if (line.description.length >= 2) setProductSearches(prev => ({ ...prev, [idx]: line.description })); }}
                    onBlur={() => { setTimeout(() => setProductResults(prev => ({ ...prev, [idx]: [] })), 200); }}
                    required
                  />
                  {(productResults[idx] || []).length > 0 && (
                    <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                      {productResults[idx].map(p => (
                        <div key={p.id} onMouseDown={() => selectProduct(idx, p)} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)' }}
                          onMouseEnter={(e) => e.target.style.background = 'var(--gray-50)'}
                          onMouseLeave={(e) => e.target.style.background = 'white'}>
                          <strong>{p.name}</strong>
                          <span style={{ color: 'var(--gray-400)', marginLeft: '8px', fontSize: '0.85rem' }}>{parseFloat(p.selling_price || 0).toFixed(2)} EUR</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="form-group" style={{ maxWidth: '80px' }}>
                  {idx === 0 && <label className="form-label">Qte</label>}
                  <input type="number" className="form-input" placeholder="Qte" value={line.quantity} onChange={(e) => updateLine(idx, 'quantity', e.target.value)} />
                </div>
                <div className="form-group" style={{ maxWidth: '120px' }}>
                  {idx === 0 && <label className="form-label">Prix HT</label>}
                  <input type="number" step="0.01" className="form-input" placeholder="Prix HT" value={line.unit_price} onChange={(e) => updateLine(idx, 'unit_price', e.target.value)} required />
                </div>
                <div className="form-group" style={{ maxWidth: '80px' }}>
                  {idx === 0 && <label className="form-label">TVA%</label>}
                  <input type="number" step="0.01" className="form-input" placeholder="TVA%" value={line.vat_rate} onChange={(e) => updateLine(idx, 'vat_rate', e.target.value)} />
                </div>
                <div className="form-group" style={{ maxWidth: '100px' }}>
                  {idx === 0 && <label className="form-label">Total HT</label>}
                  <input className="form-input" value={lineTotal(line) + ' EUR'} disabled style={{ background: 'var(--gray-100)' }} />
                </div>
                <div>
                  {form.lines.length > 1 && (
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeLine(idx)} title="Supprimer">X</button>
                  )}
                </div>
              </div>
            ))}
            <button type="button" className="btn btn-secondary btn-sm" onClick={addLine} style={{ marginBottom: '16px' }}>+ Ajouter une ligne</button>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Creer la facture</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <input
            className="form-input"
            placeholder="Rechercher par nom client ou n° facture..."
            value={filterSearch}
            onChange={(e) => setFilterSearch(e.target.value)}
            style={{ flex: 1 }}
          />
          <select className="form-select" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ maxWidth: '180px' }}>
            <option value="">Tous les statuts</option>
            {Object.entries(statusLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr><th>N°</th><th>Date</th><th>Client</th><th>HT</th><th>TVA</th><th>TTC</th><th>Paye</th><th>Statut</th></tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td style={{ fontFamily: 'monospace' }}>
                    <Link to={`/invoices/${inv.id}`} className="table-link">{inv.invoice_number}</Link>
                  </td>
                  <td>{inv.issue_date}</td>
                  <td>{inv.client_name || `#${inv.client_id}`}</td>
                  <td>{parseFloat(inv.subtotal).toFixed(2)}</td>
                  <td>{parseFloat(inv.total_vat).toFixed(2)}</td>
                  <td style={{ fontWeight: 600 }}>{parseFloat(inv.total).toFixed(2)} EUR</td>
                  <td>{parseFloat(inv.amount_paid).toFixed(2)}</td>
                  <td>
                    <span className={`badge badge-${statusColors[inv.status]}`}>
                      {statusLabels[inv.status]}
                    </span>
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr><td colSpan="8" className="table-empty">Aucune facture</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
