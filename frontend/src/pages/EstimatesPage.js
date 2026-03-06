import React, { useState, useEffect } from 'react';
import { billingAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function EstimatesPage() {
  const [estimates, setEstimates] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    client_id: '', animal_id: '',
    lines: [{ description: '', quantity: '1', unit_price: '', vat_rate: '20.00' }],
  });

  const load = async () => {
    try {
      const res = await billingAPI.listEstimates({});
      setEstimates(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => { load(); }, []);

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
      await billingAPI.createEstimate({
        client_id: parseInt(form.client_id),
        animal_id: form.animal_id ? parseInt(form.animal_id) : null,
        lines: form.lines.map((l) => ({
          description: l.description,
          quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price),
          vat_rate: parseFloat(l.vat_rate),
        })),
      });
      toast.success('Devis créé');
      setShowForm(false);
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  const convertToInvoice = async (estimateId) => {
    try {
      await billingAPI.convertEstimateToInvoice({ estimate_id: estimateId });
      toast.success('Devis converti en facture');
      load();
    } catch {
      toast.error('Erreur de conversion');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Devis</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouveau devis</button>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau devis</h3>
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
            {form.lines.map((line, idx) => (
              <div className="form-row" key={idx} style={{ marginBottom: '8px' }}>
                <div className="form-group"><input className="form-input" placeholder="Description" value={line.description} onChange={(e) => updateLine(idx, 'description', e.target.value)} required /></div>
                <div className="form-group" style={{ maxWidth: '100px' }}><input type="number" className="form-input" placeholder="Qté" value={line.quantity} onChange={(e) => updateLine(idx, 'quantity', e.target.value)} /></div>
                <div className="form-group" style={{ maxWidth: '120px' }}><input type="number" step="0.01" className="form-input" placeholder="Prix HT" value={line.unit_price} onChange={(e) => updateLine(idx, 'unit_price', e.target.value)} required /></div>
                <div className="form-group" style={{ maxWidth: '80px' }}><input type="number" className="form-input" placeholder="TVA%" value={line.vat_rate} onChange={(e) => updateLine(idx, 'vat_rate', e.target.value)} /></div>
              </div>
            ))}
            <button type="button" className="btn btn-secondary btn-sm" onClick={addLine} style={{ marginBottom: '16px' }}>+ Ligne</button>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Créer le devis</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead><tr><th>N°</th><th>Date</th><th>Client</th><th>Total TTC</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody>
              {estimates.map((est) => (
                <tr key={est.id}>
                  <td style={{ fontFamily: 'monospace' }}>{est.estimate_number}</td>
                  <td>{est.issue_date}</td>
                  <td>{est.client_id}</td>
                  <td style={{ fontWeight: 600 }}>{parseFloat(est.total).toFixed(2)} EUR</td>
                  <td><span className={`badge badge-${est.status === 'accepted' ? 'green' : est.status === 'invoiced' ? 'purple' : 'blue'}`}>{est.status}</span></td>
                  <td>
                    {est.status !== 'invoiced' && est.status !== 'rejected' && (
                      <button className="btn btn-primary btn-sm" onClick={() => convertToInvoice(est.id)}>
                        Convertir en facture
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {estimates.length === 0 && (
                <tr><td colSpan="6" style={{ textAlign: 'center', color: 'var(--gray-400)' }}>Aucun devis</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
