import React, { useState, useEffect } from 'react';
import { billingAPI } from '../services/api';
import toast from 'react-hot-toast';

const statusLabels = {
  draft: 'Brouillon', sent: 'Envoyée', paid: 'Payée',
  partial: 'Partielle', overdue: 'Impayée', cancelled: 'Annulée',
};
const statusColors = {
  draft: 'gray', sent: 'blue', paid: 'green',
  partial: 'amber', overdue: 'red', cancelled: 'gray',
};

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    client_id: '', animal_id: '', lines: [{ description: '', quantity: '1', unit_price: '', vat_rate: '20.00' }],
  });

  useEffect(() => {
    async function load() {
      try {
        const res = await billingAPI.listInvoices({});
        setInvoices(res.data);
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, []);

  const addLine = () => {
    setForm({ ...form, lines: [...form.lines, { description: '', quantity: '1', unit_price: '', vat_rate: '20.00' }] });
  };

  const updateLine = (idx, field, value) => {
    const lines = [...form.lines];
    lines[idx][field] = value;
    setForm({ ...form, lines });
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
      toast.success('Facture créée');
      setShowForm(false);
      const res = await billingAPI.listInvoices({});
      setInvoices(res.data);
    } catch {
      toast.error('Erreur lors de la création');
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
              <div className="form-group">
                <label className="form-label">ID Client *</label>
                <input className="form-input" value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">ID Animal</label>
                <input className="form-input" value={form.animal_id} onChange={(e) => setForm({ ...form, animal_id: e.target.value })} />
              </div>
            </div>
            <h4 style={{ marginBottom: '8px' }}>Lignes de facture</h4>
            {form.lines.map((line, idx) => (
              <div className="line-item-row" key={idx}>
                <div className="form-group">
                  <input className="form-input" placeholder="Description" value={line.description} onChange={(e) => updateLine(idx, 'description', e.target.value)} required />
                </div>
                <div className="form-group" style={{ maxWidth: '100px' }}>
                  <input type="number" className="form-input" placeholder="Qté" value={line.quantity} onChange={(e) => updateLine(idx, 'quantity', e.target.value)} />
                </div>
                <div className="form-group" style={{ maxWidth: '120px' }}>
                  <input type="number" step="0.01" className="form-input" placeholder="Prix HT" value={line.unit_price} onChange={(e) => updateLine(idx, 'unit_price', e.target.value)} required />
                </div>
                <div className="form-group" style={{ maxWidth: '80px' }}>
                  <input type="number" step="0.01" className="form-input" placeholder="TVA%" value={line.vat_rate} onChange={(e) => updateLine(idx, 'vat_rate', e.target.value)} />
                </div>
              </div>
            ))}
            <button type="button" className="btn btn-secondary btn-sm" onClick={addLine} style={{ marginBottom: '16px' }}>+ Ajouter une ligne</button>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Créer la facture</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr><th>N°</th><th>Date</th><th>Client</th><th>HT</th><th>TVA</th><th>TTC</th><th>Payé</th><th>Statut</th></tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td style={{ fontFamily: 'monospace' }}>{inv.invoice_number}</td>
                  <td>{inv.issue_date}</td>
                  <td>{inv.client_id}</td>
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
