import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { billingAPI, clientsAPI, animalsAPI } from '../services/api';
import toast from 'react-hot-toast';

const statusLabels = {
  draft: 'Brouillon', sent: 'Envoyee', paid: 'Payee',
  partial: 'Partielle', overdue: 'Impayee', cancelled: 'Annulee',
};
const statusColors = {
  draft: 'gray', sent: 'blue', paid: 'green',
  partial: 'amber', overdue: 'red', cancelled: 'gray',
};

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [clientName, setClientName] = useState('');
  const [animalName, setAnimalName] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const res = await billingAPI.getInvoice(id);
        const inv = res.data;
        setInvoice(inv);

        if (inv.client_id) {
          try {
            const cRes = await clientsAPI.get(inv.client_id);
            setClientName(`${cRes.data.last_name} ${cRes.data.first_name}`);
          } catch {}
        }
        if (inv.animal_id) {
          try {
            const aRes = await animalsAPI.get(inv.animal_id);
            setAnimalName(aRes.data.name);
          } catch {}
        }
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, [id]);

  if (!invoice) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/invoices" className="breadcrumb-link">Factures /</Link>
          <h1 className="page-title">{invoice.invoice_number}</h1>
        </div>
        <div className="page-header-actions">
          <span className={`badge badge-${statusColors[invoice.status]}`}>
            {statusLabels[invoice.status]}
          </span>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">HT</div>
          <div><div className="stat-value">{parseFloat(invoice.subtotal).toFixed(2)}</div><div className="stat-label">Sous-total HT</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">TVA</div>
          <div><div className="stat-value">{parseFloat(invoice.total_vat).toFixed(2)}</div><div className="stat-label">TVA</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">TTC</div>
          <div><div className="stat-value">{parseFloat(invoice.total).toFixed(2)} EUR</div><div className="stat-label">Total TTC</div></div>
        </div>
        <div className="stat-card">
          <div className={`stat-icon ${parseFloat(invoice.amount_paid) >= parseFloat(invoice.total) ? 'green' : 'red'}`}>
            PAY
          </div>
          <div><div className="stat-value">{parseFloat(invoice.amount_paid).toFixed(2)} EUR</div><div className="stat-label">Paye</div></div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Details</h3>
        <div className="form-row">
          <div><strong>Date d'emission:</strong> {invoice.issue_date}</div>
          <div><strong>Date d'echeance:</strong> {invoice.due_date || '-'}</div>
          <div>
            <strong>Client:</strong>{' '}
            {invoice.client_id ? (
              <Link to={`/clients/${invoice.client_id}`} className="table-link">{clientName || `#${invoice.client_id}`}</Link>
            ) : '-'}
          </div>
          <div>
            <strong>Animal:</strong>{' '}
            {invoice.animal_id ? (
              <Link to={`/animals/${invoice.animal_id}`} className="table-link">{animalName || `#${invoice.animal_id}`}</Link>
            ) : '-'}
          </div>
        </div>
        {invoice.notes && (
          <div style={{ marginTop: '12px' }}>
            <strong>Notes:</strong>
            <p style={{ whiteSpace: 'pre-wrap', marginTop: '4px' }}>{invoice.notes}</p>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Lignes de facture</h3>
        <table>
          <thead>
            <tr><th>Description</th><th>Qte</th><th>Prix unitaire HT</th><th>TVA %</th><th>Total HT</th></tr>
          </thead>
          <tbody>
            {(invoice.lines || []).map((line, idx) => (
              <tr key={idx}>
                <td>{line.description}</td>
                <td>{parseFloat(line.quantity)}</td>
                <td>{parseFloat(line.unit_price).toFixed(2)} EUR</td>
                <td>{parseFloat(line.vat_rate).toFixed(0)}%</td>
                <td style={{ fontWeight: 600 }}>{parseFloat(line.line_total).toFixed(2)} EUR</td>
              </tr>
            ))}
            {(!invoice.lines || invoice.lines.length === 0) && (
              <tr><td colSpan="5" className="table-empty">Aucune ligne</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
