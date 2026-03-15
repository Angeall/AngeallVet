import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { billingAPI, clientsAPI, animalsAPI, settingsAPI, authAPI } from '../services/api';
import toast from 'react-hot-toast';

const statusLabels = {
  draft: 'Brouillon', sent: 'Envoyee', paid: 'Payee',
  partial: 'Partielle', overdue: 'Impayee', cancelled: 'Annulee',
};
const statusColors = {
  draft: 'gray', sent: 'blue', paid: 'green',
  partial: 'amber', overdue: 'red', cancelled: 'gray',
};
const methodLabels = {
  cash: 'Especes', card: 'Carte bancaire', vivacom: 'Terminal Viva.com',
  check: 'Cheque', transfer: 'Virement',
};

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [clientName, setClientName] = useState('');
  const [animalName, setAnimalName] = useState('');

  // Payment modal state
  const [showPayModal, setShowPayModal] = useState(false);
  const [payStep, setPayStep] = useState('choose'); // choose, cash, card, vivacom, split
  const [payAmount, setPayAmount] = useState('');
  const [cashReceived, setCashReceived] = useState('');

  // Split payment state
  const [splitLines, setSplitLines] = useState([
    { method: 'cash', amount: '' },
    { method: 'card', amount: '' },
  ]);

  // Debt acknowledgment
  const [showDebtDoc, setShowDebtDoc] = useState(false);
  const [debtData, setDebtData] = useState(null);

  // Veterinarians management
  const [staff, setStaff] = useState([]);
  const [showAddVet, setShowAddVet] = useState(false);

  useEffect(() => {
    authAPI.listStaff().then(res => setStaff(res.data || [])).catch(() => {});
  }, []);

  const addVet = async (userId) => {
    try {
      await billingAPI.addInvoiceVet(id, userId);
      toast.success('Veterinaire ajoute');
      setShowAddVet(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const removeVet = async (userId) => {
    try {
      await billingAPI.removeInvoiceVet(id, userId);
      toast.success('Veterinaire retire');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const load = async () => {
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
  };

  useEffect(() => { load(); }, [id]);

  const remaining = invoice ? parseFloat(invoice.total) - parseFloat(invoice.amount_paid) : 0;

  const openPayModal = () => {
    setPayStep('choose');
    setPayAmount(remaining.toFixed(2));
    setCashReceived('');
    setSplitLines([
      { method: 'cash', amount: '' },
      { method: 'card', amount: '' },
    ]);
    setShowPayModal(true);
  };

  const submitPayment = async (method, amount) => {
    try {
      await billingAPI.recordPayment({
        invoice_id: parseInt(id),
        amount: parseFloat(amount),
        payment_method: method,
      });
      return true;
    } catch {
      toast.error('Erreur lors du paiement');
      return false;
    }
  };

  // Single payment (cash/card/vivacom)
  const handleSinglePay = async (method) => {
    const amt = parseFloat(payAmount);
    if (!amt || amt <= 0) { toast.error('Montant invalide'); return; }
    const ok = await submitPayment(method, amt);
    if (ok) {
      toast.success(`Paiement de ${amt.toFixed(2)} EUR (${methodLabels[method]}) enregistre`);
      setShowPayModal(false);
      load();
    }
  };

  // Split payment
  const handleSplitPay = async () => {
    const validLines = splitLines.filter(l => parseFloat(l.amount) > 0);
    if (validLines.length === 0) { toast.error('Ajoutez au moins un paiement'); return; }
    const total = validLines.reduce((s, l) => s + parseFloat(l.amount || 0), 0);
    if (total <= 0) { toast.error('Le montant total doit etre positif'); return; }

    let allOk = true;
    for (const line of validLines) {
      const ok = await submitPayment(line.method, parseFloat(line.amount));
      if (!ok) { allOk = false; break; }
    }
    if (allOk) {
      toast.success(`Paiement multiple de ${total.toFixed(2)} EUR enregistre`);
      setShowPayModal(false);
      load();
    }
  };

  const addSplitLine = () => {
    setSplitLines([...splitLines, { method: 'cash', amount: '' }]);
  };

  const removeSplitLine = (idx) => {
    setSplitLines(splitLines.filter((_, i) => i !== idx));
  };

  const updateSplitLine = (idx, field, value) => {
    const updated = [...splitLines];
    updated[idx] = { ...updated[idx], [field]: value };
    setSplitLines(updated);
  };

  const splitTotal = splitLines.reduce((s, l) => s + (parseFloat(l.amount) || 0), 0);

  // Cash calculator
  const cashAmount = parseFloat(payAmount) || 0;
  const cashReceivedVal = parseFloat(cashReceived) || 0;
  const cashChange = cashReceivedVal - cashAmount;

  const openDebtAcknowledgment = async () => {
    try {
      const res = await billingAPI.getDebtAcknowledgment(id);
      setDebtData(res.data);
      setShowDebtDoc(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const printDebtDoc = () => {
    const printWindow = window.open('', '_blank');
    const clinic = debtData.clinic;
    const client = debtData.client;
    const inv = debtData.invoice;
    const today = new Date().toLocaleDateString('fr-FR');

    printWindow.document.write(`<!DOCTYPE html><html><head><title>Reconnaissance de dette - ${inv.invoice_number}</title>
      <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; line-height: 1.6; }
        h1 { text-align: center; font-size: 1.4rem; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 1px; }
        .header { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .header-block { max-width: 45%; }
        .header-block h3 { margin: 0 0 8px; font-size: 0.9rem; color: #666; text-transform: uppercase; }
        .header-block p { margin: 2px 0; font-size: 0.9rem; }
        .separator { border: none; border-top: 2px solid #333; margin: 24px 0; }
        .content { margin: 20px 0; font-size: 0.95rem; }
        .amount { font-size: 1.3rem; font-weight: 700; text-align: center; margin: 20px 0; padding: 16px; border: 2px solid #333; }
        .legal { font-size: 0.8rem; color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 16px; }
        .signature { margin-top: 60px; display: flex; justify-content: space-between; }
        .signature-block { width: 40%; text-align: center; }
        .signature-line { border-top: 1px solid #333; margin-top: 60px; padding-top: 8px; font-size: 0.85rem; }
        @media print { body { margin: 20px; } }
      </style></head><body>
      <h1>Reconnaissance de dette</h1>
      <div class="header">
        <div class="header-block">
          <h3>Creancier</h3>
          <p><strong>${clinic.clinic_name || ''}</strong></p>
          <p>${clinic.address || ''}</p>
          <p>${clinic.postal_code || ''} ${clinic.city || ''}</p>
          ${clinic.siret ? `<p>SIRET : ${clinic.siret}</p>` : ''}
          ${clinic.vat_number ? `<p>TVA : ${clinic.vat_number}</p>` : ''}
        </div>
        <div class="header-block">
          <h3>Debiteur</h3>
          <p><strong>${client.last_name} ${client.first_name}</strong></p>
          <p>${client.address || ''}</p>
          <p>${client.postal_code || ''} ${client.city || ''}</p>
          ${client.vat_number ? `<p>TVA : ${client.vat_number}</p>` : ''}
        </div>
      </div>
      <hr class="separator" />
      <div class="content">
        <p>Je soussigne(e), <strong>${client.last_name} ${client.first_name}</strong>, reconnais devoir a
        <strong>${clinic.clinic_name || 'la clinique veterinaire'}</strong> la somme de :</p>
      </div>
      <div class="amount">${inv.remaining.toFixed(2)} EUR</div>
      <div class="content">
        <p>Au titre de la facture n° <strong>${inv.invoice_number}</strong> emise le ${inv.issue_date || '-'},
        d'un montant total de ${inv.total.toFixed(2)} EUR TTC, dont ${inv.amount_paid.toFixed(2)} EUR deja regles.</p>
        <p>Je m'engage a rembourser cette somme dans les meilleurs delais.</p>
      </div>
      <div class="content">
        <p>Fait a ${clinic.city || '________________'}, le ${today}</p>
      </div>
      <div class="signature">
        <div class="signature-block">
          <div class="signature-line">Signature du debiteur<br/>(precedee de la mention "Lu et approuve")</div>
        </div>
        <div class="signature-block">
          <div class="signature-line">Signature du creancier</div>
        </div>
      </div>
      <div class="legal">
        <p>Document etabli en deux exemplaires originaux, un pour chaque partie.</p>
        <p>Conformement aux articles 1326 et suivants du Code civil, la presente reconnaissance de dette constitue un engagement unilateral du debiteur.</p>
      </div>
      </body></html>`);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 300);
  };

  if (!invoice) return <div className="page-content">Chargement...</div>;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <nav className="page-breadcrumb">
            <Link to="/invoices">Factures</Link>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{invoice.invoice_number}</span>
          </nav>
          <h1 className="page-title">{invoice.invoice_number}</h1>
        </div>
        <div className="page-header-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className={`badge badge-${statusColors[invoice.status]}`}>
            {statusLabels[invoice.status]}
          </span>
          {invoice.status !== 'paid' && invoice.status !== 'cancelled' && remaining > 0 && (
            <>
              <button className="btn btn-secondary" onClick={openDebtAcknowledgment}>
                Reconnaissance de dette
              </button>
              <button className="btn btn-primary" onClick={openPayModal}>
                Payer maintenant
              </button>
            </>
          )}
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
          <div className={`stat-icon ${remaining <= 0 ? 'green' : 'red'}`}>
            {remaining <= 0 ? 'OK' : 'DU'}
          </div>
          <div>
            <div className="stat-value">{remaining > 0 ? remaining.toFixed(2) : parseFloat(invoice.amount_paid).toFixed(2)} EUR</div>
            <div className="stat-label">{remaining > 0 ? 'Reste a payer' : 'Paye'}</div>
          </div>
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
        {/* Veterinarians */}
        <div style={{ marginTop: '16px', borderTop: '1px solid var(--gray-100)', paddingTop: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <strong>Veterinaires:</strong>
            {(invoice.veterinarians || []).map(v => (
              <span key={v.id} className="badge badge-blue" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                {v.user_name || `#${v.user_id}`}
                <button onClick={() => removeVet(v.user_id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, marginLeft: '4px', fontSize: '0.9em', lineHeight: 1 }}>x</button>
              </span>
            ))}
            {(!invoice.veterinarians || invoice.veterinarians.length === 0) && <span style={{ color: 'var(--gray-400)', fontSize: '0.85rem' }}>Aucun</span>}
            <button className="btn btn-secondary btn-sm" onClick={() => setShowAddVet(!showAddVet)} style={{ marginLeft: '4px' }}>+</button>
          </div>
          {showAddVet && (
            <select className="form-select" style={{ maxWidth: '250px' }} onChange={(e) => { if (e.target.value) { addVet(parseInt(e.target.value)); e.target.value = ''; } }}>
              <option value="">-- Ajouter un collegue --</option>
              {staff.filter(s => !(invoice.veterinarians || []).some(v => v.user_id === s.id)).map(s => (
                <option key={s.id} value={s.id}>{s.first_name} {s.last_name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Lignes de facture</h3>
        <table>
          <thead>
            <tr><th>Description</th><th>Qte</th><th>Prix unitaire HT</th><th>TVA %</th><th>N Lot</th><th>Total HT</th></tr>
          </thead>
          <tbody>
            {(invoice.lines || []).map((line, idx) => (
              <tr key={idx}>
                <td>{line.description}</td>
                <td>{parseFloat(line.quantity)}</td>
                <td>{parseFloat(line.unit_price).toFixed(2)} EUR</td>
                <td>{parseFloat(line.vat_rate).toFixed(0)}%</td>
                <td>{line.lot_number || '-'}</td>
                <td style={{ fontWeight: 600 }}>{parseFloat(line.line_total).toFixed(2)} EUR</td>
              </tr>
            ))}
            {(!invoice.lines || invoice.lines.length === 0) && (
              <tr><td colSpan="6" className="table-empty">Aucune ligne</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Payment history */}
      {(invoice.payments || []).length > 0 && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Historique des paiements</h3>
          <table>
            <thead>
              <tr><th>Date</th><th>Methode</th><th>Montant</th><th>Reference</th></tr>
            </thead>
            <tbody>
              {invoice.payments.map((p, idx) => (
                <tr key={idx}>
                  <td>{p.payment_date || '-'}</td>
                  <td><span className={`badge badge-${p.payment_method === 'cash' ? 'green' : p.payment_method === 'card' ? 'blue' : p.payment_method === 'vivacom' ? 'purple' : 'amber'}`}>
                    {methodLabels[p.payment_method] || p.payment_method}
                  </span></td>
                  <td style={{ fontWeight: 600 }}>{parseFloat(p.amount).toFixed(2)} EUR</td>
                  <td>{p.reference || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Debt Acknowledgment Modal ─────────────────────────── */}
      {showDebtDoc && debtData && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowDebtDoc(false); }}>
          <div style={{ background: 'white', borderRadius: '12px', width: '500px', maxHeight: '90vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--gray-100)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Reconnaissance de dette</h2>
              <button onClick={() => setShowDebtDoc(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.3rem', color: 'var(--gray-400)' }}>&#x2715;</button>
            </div>
            <div style={{ padding: '24px' }}>
              <div style={{ marginBottom: '16px' }}>
                <strong>Cabinet :</strong> {debtData.clinic.clinic_name || '-'}
              </div>
              <div style={{ marginBottom: '16px' }}>
                <strong>Client :</strong> {debtData.client.last_name} {debtData.client.first_name}
              </div>
              <div style={{ marginBottom: '16px' }}>
                <strong>Facture :</strong> {debtData.invoice.invoice_number}
              </div>
              <div style={{ background: '#fef2f2', borderRadius: '8px', padding: '16px', textAlign: 'center', marginBottom: '16px' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>Montant restant du</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ef4444' }}>{debtData.invoice.remaining.toFixed(2)} EUR</div>
              </div>
              <button className="btn btn-primary" style={{ width: '100%' }} onClick={printDebtDoc}>
                Imprimer la reconnaissance de dette
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Payment Modal ──────────────────────────────────────── */}
      {showPayModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowPayModal(false); }}>
          <div style={{ background: 'white', borderRadius: '12px', width: '520px', maxHeight: '90vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>

            {/* Modal header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--gray-100)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Encaisser {invoice.invoice_number}</h2>
                <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginTop: '4px' }}>
                  Reste a payer : <strong style={{ color: 'var(--red, #ef4444)' }}>{remaining.toFixed(2)} EUR</strong>
                </div>
              </div>
              <button onClick={() => setShowPayModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.3rem', color: 'var(--gray-400)' }}>
                &#x2715;
              </button>
            </div>

            <div style={{ padding: '24px' }}>
              {/* ── Step: Choose method ── */}
              {payStep === 'choose' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <PayMethodCard
                    icon={<CashIcon />}
                    label="Especes"
                    description="Paiement en liquide avec calculette de rendu"
                    color="#10b981"
                    onClick={() => { setPayStep('cash'); setPayAmount(remaining.toFixed(2)); setCashReceived(''); }}
                  />
                  <PayMethodCard
                    icon={<CardIcon />}
                    label="Carte bancaire"
                    description="Paiement par carte classique"
                    color="#3b82f6"
                    onClick={() => { setPayStep('card'); setPayAmount(remaining.toFixed(2)); }}
                  />
                  <PayMethodCard
                    icon={<TerminalIcon />}
                    label="Terminal Viva.com"
                    description="Paiement via terminal Viva.com"
                    color="#8b5cf6"
                    onClick={() => { setPayStep('vivacom'); setPayAmount(remaining.toFixed(2)); }}
                  />
                  <PayMethodCard
                    icon={<SplitIcon />}
                    label="Paiement multiple"
                    description="Combiner plusieurs moyens de paiement"
                    color="#f59e0b"
                    onClick={() => {
                      setPayStep('split');
                      setSplitLines([
                        { method: 'cash', amount: '' },
                        { method: 'card', amount: '' },
                      ]);
                    }}
                  />
                </div>
              )}

              {/* ── Step: Cash ── */}
              {payStep === 'cash' && (
                <div>
                  <button onClick={() => setPayStep('choose')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', marginBottom: '16px', padding: 0 }}>
                    &larr; Retour
                  </button>
                  <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#10b981' }}><CashIcon /></span> Paiement en especes
                  </h3>

                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label className="form-label">Montant a encaisser (EUR)</label>
                    <input type="number" className="form-input" value={payAmount}
                      onChange={(e) => setPayAmount(e.target.value)} step="0.01" min="0.01"
                      style={{ fontSize: '1.2rem', fontWeight: 700, textAlign: 'center' }} />
                  </div>

                  {/* Cash calculator */}
                  <div style={{ background: 'var(--gray-50, #f9fafb)', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
                    <div className="form-group" style={{ marginBottom: '12px' }}>
                      <label className="form-label">Argent recu (EUR)</label>
                      <input type="number" className="form-input" value={cashReceived}
                        onChange={(e) => setCashReceived(e.target.value)} step="0.01" min="0"
                        placeholder="Saisir le montant recu..."
                        style={{ fontSize: '1.2rem', fontWeight: 700, textAlign: 'center' }} autoFocus />
                    </div>

                    {/* Quick cash buttons */}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
                      {[5, 10, 20, 50, 100, 200].map(v => (
                        <button key={v} type="button" className="btn btn-secondary btn-sm"
                          onClick={() => setCashReceived(String(v))}
                          style={{ minWidth: '50px' }}>
                          {v} EUR
                        </button>
                      ))}
                      <button type="button" className="btn btn-secondary btn-sm"
                        onClick={() => setCashReceived(payAmount)}
                        style={{ background: '#10b981', color: 'white', border: 'none' }}>
                        Exact
                      </button>
                    </div>

                    {cashReceivedVal > 0 && (
                      <div style={{
                        textAlign: 'center', padding: '16px', borderRadius: '8px',
                        background: cashChange >= 0 ? '#ecfdf5' : '#fef2f2',
                        border: `2px solid ${cashChange >= 0 ? '#10b981' : '#ef4444'}`,
                      }}>
                        {cashChange >= 0 ? (
                          <>
                            <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>A rendre au client</div>
                            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#10b981' }}>
                              {cashChange.toFixed(2)} EUR
                            </div>
                          </>
                        ) : (
                          <>
                            <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>Montant insuffisant</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ef4444' }}>
                              Manque {Math.abs(cashChange).toFixed(2)} EUR
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  <button className="btn btn-primary" style={{ width: '100%', fontSize: '1rem', padding: '12px' }}
                    onClick={() => handleSinglePay('cash')}
                    disabled={cashAmount <= 0}>
                    Valider le paiement en especes - {cashAmount.toFixed(2)} EUR
                  </button>
                </div>
              )}

              {/* ── Step: Card ── */}
              {payStep === 'card' && (
                <div>
                  <button onClick={() => setPayStep('choose')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', marginBottom: '16px', padding: 0 }}>
                    &larr; Retour
                  </button>
                  <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#3b82f6' }}><CardIcon /></span> Paiement par carte bancaire
                  </h3>

                  <div className="form-group" style={{ marginBottom: '16px' }}>
                    <label className="form-label">Montant (EUR)</label>
                    <input type="number" className="form-input" value={payAmount}
                      onChange={(e) => setPayAmount(e.target.value)} step="0.01" min="0.01"
                      style={{ fontSize: '1.2rem', fontWeight: 700, textAlign: 'center' }} />
                  </div>

                  <div style={{ background: '#eff6ff', borderRadius: '8px', padding: '16px', marginBottom: '16px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>Montant a debiter</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#3b82f6' }}>{(parseFloat(payAmount) || 0).toFixed(2)} EUR</div>
                  </div>

                  <button className="btn btn-primary" style={{ width: '100%', fontSize: '1rem', padding: '12px' }}
                    onClick={() => handleSinglePay('card')}
                    disabled={(parseFloat(payAmount) || 0) <= 0}>
                    Confirmer le paiement CB - {(parseFloat(payAmount) || 0).toFixed(2)} EUR
                  </button>
                </div>
              )}

              {/* ── Step: Viva.com ── */}
              {payStep === 'vivacom' && (
                <div>
                  <button onClick={() => setPayStep('choose')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', marginBottom: '16px', padding: 0 }}>
                    &larr; Retour
                  </button>
                  <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#8b5cf6' }}><TerminalIcon /></span> Terminal Viva.com
                  </h3>

                  <div className="form-group" style={{ marginBottom: '16px' }}>
                    <label className="form-label">Montant (EUR)</label>
                    <input type="number" className="form-input" value={payAmount}
                      onChange={(e) => setPayAmount(e.target.value)} step="0.01" min="0.01"
                      style={{ fontSize: '1.2rem', fontWeight: 700, textAlign: 'center' }} />
                  </div>

                  <div style={{ background: '#f5f3ff', borderRadius: '8px', padding: '16px', marginBottom: '16px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>Envoi au terminal Viva.com</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#8b5cf6' }}>{(parseFloat(payAmount) || 0).toFixed(2)} EUR</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '8px' }}>
                      L'integration avec les terminaux Viva.com sera disponible prochainement.
                      <br />Pour l'instant, validez manuellement apres encaissement sur le terminal.
                    </div>
                  </div>

                  <button className="btn btn-primary" style={{ width: '100%', fontSize: '1rem', padding: '12px', background: '#8b5cf6', borderColor: '#8b5cf6' }}
                    onClick={() => handleSinglePay('vivacom')}
                    disabled={(parseFloat(payAmount) || 0) <= 0}>
                    Confirmer paiement Viva.com - {(parseFloat(payAmount) || 0).toFixed(2)} EUR
                  </button>
                </div>
              )}

              {/* ── Step: Split payment ── */}
              {payStep === 'split' && (
                <div>
                  <button onClick={() => setPayStep('choose')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', marginBottom: '16px', padding: 0 }}>
                    &larr; Retour
                  </button>
                  <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#f59e0b' }}><SplitIcon /></span> Paiement multiple
                  </h3>

                  <div style={{ marginBottom: '8px', fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                    Reste a couvrir : <strong>{remaining.toFixed(2)} EUR</strong> | Reparti : <strong style={{ color: splitTotal >= remaining - 0.01 ? '#10b981' : '#ef4444' }}>{splitTotal.toFixed(2)} EUR</strong>
                  </div>

                  {splitLines.map((line, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
                      <select className="form-select" value={line.method}
                        onChange={(e) => updateSplitLine(idx, 'method', e.target.value)}
                        style={{ width: '180px' }}>
                        <option value="cash">Especes</option>
                        <option value="card">Carte bancaire</option>
                        <option value="vivacom">Viva.com</option>
                        <option value="check">Cheque</option>
                        <option value="transfer">Virement</option>
                      </select>
                      <input type="number" className="form-input" value={line.amount}
                        onChange={(e) => updateSplitLine(idx, 'amount', e.target.value)}
                        placeholder="Montant" step="0.01" min="0" style={{ flex: 1 }} />
                      <span style={{ fontSize: '0.85rem', color: 'var(--gray-400)' }}>EUR</span>
                      {splitLines.length > 1 && (
                        <button className="btn btn-secondary btn-sm" onClick={() => removeSplitLine(idx)} style={{ color: 'red' }}>&#x2715;</button>
                      )}
                    </div>
                  ))}

                  <button type="button" className="btn btn-secondary btn-sm" onClick={addSplitLine} style={{ marginBottom: '16px' }}>
                    + Ajouter un moyen de paiement
                  </button>

                  {/* Auto-fill remaining */}
                  <div style={{ marginBottom: '16px' }}>
                    <button type="button" className="btn btn-secondary btn-sm"
                      onClick={() => {
                        const filled = splitLines.reduce((s, l, i) => i < splitLines.length - 1 ? s + (parseFloat(l.amount) || 0) : s, 0);
                        const rest = Math.max(0, remaining - filled);
                        const updated = [...splitLines];
                        updated[updated.length - 1] = { ...updated[updated.length - 1], amount: rest.toFixed(2) };
                        setSplitLines(updated);
                      }}>
                      Completer le dernier montant automatiquement
                    </button>
                  </div>

                  <div style={{ background: 'var(--gray-50, #f9fafb)', borderRadius: '8px', padding: '12px', marginBottom: '16px' }}>
                    <table style={{ width: '100%', fontSize: '0.85rem' }}>
                      <tbody>
                        {splitLines.filter(l => parseFloat(l.amount) > 0).map((l, i) => (
                          <tr key={i}>
                            <td>{methodLabels[l.method] || l.method}</td>
                            <td style={{ textAlign: 'right', fontWeight: 600 }}>{parseFloat(l.amount).toFixed(2)} EUR</td>
                          </tr>
                        ))}
                        <tr style={{ borderTop: '2px solid var(--gray-200)' }}>
                          <td><strong>Total</strong></td>
                          <td style={{ textAlign: 'right', fontWeight: 700, fontSize: '1rem' }}>{splitTotal.toFixed(2)} EUR</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <button className="btn btn-primary" style={{ width: '100%', fontSize: '1rem', padding: '12px' }}
                    onClick={handleSplitPay}
                    disabled={splitTotal <= 0}>
                    Valider le paiement multiple - {splitTotal.toFixed(2)} EUR
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Payment method selection card ─────────────────────────────── */
function PayMethodCard({ icon, label, description, color, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        border: '2px solid var(--gray-200)', borderRadius: '10px', padding: '20px',
        cursor: 'pointer', textAlign: 'center', transition: 'all 0.15s',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = color; e.currentTarget.style.boxShadow = `0 0 0 1px ${color}`; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gray-200)'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      <div style={{ color, marginBottom: '8px' }}>{icon}</div>
      <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{label}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '4px' }}>{description}</div>
    </div>
  );
}

/* ── Icons ─────────────────────────────────────────────────────── */
function CashIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="20" height="12" rx="2" /><circle cx="12" cy="12" r="3" /><line x1="6" y1="12" x2="6" y2="12.01" /><line x1="18" y1="12" x2="18" y2="12.01" />
    </svg>
  );
}

function CardIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="4" width="22" height="16" rx="2" /><line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="2" width="14" height="20" rx="2" /><line x1="9" y1="14" x2="9" y2="14.01" /><line x1="12" y1="14" x2="12" y2="14.01" /><line x1="15" y1="14" x2="15" y2="14.01" />
      <line x1="9" y1="17" x2="9" y2="17.01" /><line x1="12" y1="17" x2="12" y2="17.01" /><line x1="15" y1="17" x2="15" y2="17.01" />
      <rect x="8" y="5" width="8" height="5" rx="1" />
    </svg>
  );
}

function SplitIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="2" x2="12" y2="22" /><polyline points="7 7 12 2 17 7" /><line x1="4" y1="12" x2="20" y2="12" />
      <polyline points="7 17 12 22 17 17" />
    </svg>
  );
}
