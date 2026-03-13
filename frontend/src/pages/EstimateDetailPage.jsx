import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { billingAPI, clientsAPI, animalsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function EstimateDetailPage() {
  const { id } = useParams();
  const [estimate, setEstimate] = useState(null);
  const [clientName, setClientName] = useState('');
  const [animalName, setAnimalName] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const res = await billingAPI.getEstimate(id);
        const est = res.data;
        setEstimate(est);

        if (est.client_id) {
          try {
            const cRes = await clientsAPI.get(est.client_id);
            setClientName(`${cRes.data.last_name} ${cRes.data.first_name}`);
          } catch {}
        }
        if (est.animal_id) {
          try {
            const aRes = await animalsAPI.get(est.animal_id);
            setAnimalName(aRes.data.name);
          } catch {}
        }
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, [id]);

  const convertToInvoice = async () => {
    try {
      await billingAPI.convertEstimateToInvoice({ estimate_id: estimate.id });
      toast.success('Devis converti en facture');
      const res = await billingAPI.getEstimate(id);
      setEstimate(res.data);
    } catch {
      toast.error('Erreur de conversion');
    }
  };

  if (!estimate) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <Link to="/estimates" className="breadcrumb-link">Devis /</Link>
          <h1 className="page-title">{estimate.estimate_number}</h1>
        </div>
        <div className="page-header-actions">
          <span className={`badge badge-${estimate.status === 'accepted' ? 'green' : estimate.status === 'invoiced' ? 'purple' : 'blue'}`}>
            {estimate.status}
          </span>
          {estimate.status !== 'invoiced' && estimate.status !== 'rejected' && (
            <button className="btn btn-primary" onClick={convertToInvoice} style={{ marginLeft: '8px' }}>
              Convertir en facture
            </button>
          )}
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">HT</div>
          <div><div className="stat-value">{parseFloat(estimate.subtotal).toFixed(2)}</div><div className="stat-label">Sous-total HT</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">TVA</div>
          <div><div className="stat-value">{parseFloat(estimate.total_vat).toFixed(2)}</div><div className="stat-label">TVA</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">TTC</div>
          <div><div className="stat-value">{parseFloat(estimate.total).toFixed(2)} EUR</div><div className="stat-label">Total TTC</div></div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Details</h3>
        <div className="form-row">
          <div><strong>Date d'emission:</strong> {estimate.issue_date}</div>
          <div><strong>Valide jusqu'au:</strong> {estimate.valid_until || '-'}</div>
          <div>
            <strong>Client:</strong>{' '}
            {estimate.client_id ? (
              <Link to={`/clients/${estimate.client_id}`} className="table-link">{clientName || `#${estimate.client_id}`}</Link>
            ) : '-'}
          </div>
          <div>
            <strong>Animal:</strong>{' '}
            {estimate.animal_id ? (
              <Link to={`/animals/${estimate.animal_id}`} className="table-link">{animalName || `#${estimate.animal_id}`}</Link>
            ) : '-'}
          </div>
        </div>
        {estimate.notes && (
          <div style={{ marginTop: '12px' }}>
            <strong>Notes:</strong>
            <p style={{ whiteSpace: 'pre-wrap', marginTop: '4px' }}>{estimate.notes}</p>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Lignes du devis</h3>
        <table>
          <thead>
            <tr><th>Description</th><th>Qte</th><th>Prix unitaire HT</th><th>TVA %</th><th>Total HT</th></tr>
          </thead>
          <tbody>
            {(estimate.lines || []).map((line, idx) => (
              <tr key={idx}>
                <td>{line.description}</td>
                <td>{parseFloat(line.quantity)}</td>
                <td>{parseFloat(line.unit_price).toFixed(2)} EUR</td>
                <td>{parseFloat(line.vat_rate).toFixed(0)}%</td>
                <td style={{ fontWeight: 600 }}>{parseFloat(line.line_total).toFixed(2)} EUR</td>
              </tr>
            ))}
            {(!estimate.lines || estimate.lines.length === 0) && (
              <tr><td colSpan="5" className="table-empty">Aucune ligne</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
