import React, { useState, useEffect, useCallback } from 'react';
import { accountingAPI } from '../services/api';
import { downloadBlob } from '../services/download';
import toast from 'react-hot-toast';

const methodLabels = { cash: 'Espèces', card: 'Carte', check: 'Chèque', transfer: 'Virement', stripe: 'Stripe', other: 'Autre' };
const eur = (n) => `${(Number(n) || 0).toFixed(2)} €`;

export default function AccountingPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [day, setDay] = useState(today);
  const [dayData, setDayData] = useState(null);
  const [opening, setOpening] = useState('0');
  const [counted, setCounted] = useState('');
  const [notes, setNotes] = useState('');
  const [mv, setMv] = useState({ direction: 'out', amount: '', reason: '' });
  const [closings, setClosings] = useState([]);
  const [from, setFrom] = useState(`${today.slice(0, 8)}01`);
  const [to, setTo] = useState(today);

  const load = useCallback(async () => {
    try {
      const { data } = await accountingAPI.cashDay(day);
      setDayData(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erreur de chargement');
    }
  }, [day]);

  const loadClosings = useCallback(async () => {
    try { setClosings((await accountingAPI.listClosings()).data || []); } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadClosings(); }, [loadClosings]);

  const closed = dayData?.closed;
  const z = dayData?.closing;
  const cashNet = dayData?.cash_movement_net ?? 0;
  const expected = (parseFloat(opening) || 0) + cashNet;
  const discrepancy = counted === '' ? 0 : (parseFloat(counted) || 0) - expected;

  const addMovement = async () => {
    if (!mv.amount) return;
    try {
      await accountingAPI.addMovement({ direction: mv.direction, amount: parseFloat(mv.amount), reason: mv.reason || null, business_date: day });
      setMv({ direction: 'out', amount: '', reason: '' });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erreur'); }
  };

  const closeDay = async () => {
    if (!window.confirm('Clôturer définitivement cette journée ? Aucun encaissement ne pourra plus y être ajouté.')) return;
    try {
      await accountingAPI.closeDay({ business_date: day, opening_amount: parseFloat(opening) || 0, counted_amount: parseFloat(counted) || 0, notes: notes || null });
      toast.success('Journée clôturée');
      setNotes('');
      load();
      loadClosings();
    } catch (e) { toast.error(e.response?.data?.detail || 'Erreur'); }
  };

  const doExport = async (kind) => {
    try {
      if (kind === 'journal') downloadBlob(await accountingAPI.exportJournal({ date_from: from, date_to: to }), `journal_comptable_${from}_${to}.xlsx`);
      else downloadBlob(await accountingAPI.exportFec({ date_from: from, date_to: to }), `FEC_${from}_${to}.txt`);
    } catch { toast.error("Erreur lors de l'export"); }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Comptabilité</h1>
          <span className="page-subtitle">Clôture de caisse & export comptable</span>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <h3 className="card-title" style={{ margin: 0 }}>Clôture de caisse</h3>
          <input type="date" className="form-input" style={{ width: 'auto' }} value={day} onChange={(e) => setDay(e.target.value)} />
        </div>

        {!dayData ? <p style={{ color: 'var(--gray-400)' }}>Chargement…</p> : (
          <>
            <div className="table-container">
              <table>
                <thead><tr><th>Moyen de paiement</th><th style={{ textAlign: 'right' }}>Montant encaissé</th></tr></thead>
                <tbody>
                  {Object.entries(dayData.totals_by_method).map(([m, a]) => (
                    <tr key={m}><td>{methodLabels[m] || m}</td><td style={{ textAlign: 'right' }}>{eur(a)}</td></tr>
                  ))}
                  {Object.keys(dayData.totals_by_method).length === 0 && (
                    <tr><td colSpan="2" className="table-empty">Aucun encaissement ce jour</td></tr>
                  )}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 700, borderTop: '2px solid var(--gray-200)' }}>
                    <td>Total ({dayData.payment_count})</td>
                    <td style={{ textAlign: 'right' }}>{eur(dayData.total)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {closed ? (
              <div style={{ marginTop: '16px', background: 'var(--gray-50)', borderRadius: '8px', padding: '14px' }}>
                <strong>Journée clôturée</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '8px', marginTop: '8px', fontSize: '0.9rem' }}>
                  <div>Fond de caisse : <strong>{eur(z.opening_amount)}</strong></div>
                  <div>Espèces comptées : <strong>{eur(z.counted_amount)}</strong></div>
                  <div>Espèces attendues : <strong>{eur(z.expected_amount)}</strong></div>
                  <div style={{ color: z.discrepancy === 0 ? 'inherit' : 'var(--red, #ef4444)' }}>Écart : <strong>{eur(z.discrepancy)}</strong></div>
                </div>
                {z.notes && <p style={{ marginTop: '8px', fontSize: '0.85rem', color: 'var(--gray-600)' }}>{z.notes}</p>}
              </div>
            ) : (
              <>
                <div style={{ marginTop: '16px' }}>
                  <label className="form-label">Mouvements de caisse (hors factures)</label>
                  {dayData.movements.map((m) => (
                    <div key={m.id} style={{ fontSize: '0.85rem', color: 'var(--gray-600)' }}>
                      {m.direction === 'in' ? '+ ' : '− '}{eur(m.amount)}{m.reason ? ` — ${m.reason}` : ''}
                    </div>
                  ))}
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'flex-end', marginTop: '8px' }}>
                    <select className="form-select" style={{ width: 'auto' }} value={mv.direction} onChange={(e) => setMv({ ...mv, direction: e.target.value })}>
                      <option value="out">Sortie</option>
                      <option value="in">Entrée</option>
                    </select>
                    <input type="number" step="0.01" className="form-input" style={{ maxWidth: '120px' }} placeholder="Montant" value={mv.amount} onChange={(e) => setMv({ ...mv, amount: e.target.value })} />
                    <input className="form-input" style={{ flex: '1 1 160px' }} placeholder="Motif (ex : versement banque)" value={mv.reason} onChange={(e) => setMv({ ...mv, reason: e.target.value })} />
                    <button className="btn btn-secondary" onClick={addMovement}>Ajouter</button>
                  </div>
                </div>

                <div className="form-row" style={{ marginTop: '16px' }}>
                  <div className="form-group">
                    <label className="form-label">Fond de caisse (€)</label>
                    <input type="number" step="0.01" className="form-input" value={opening} onChange={(e) => setOpening(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Espèces comptées (€)</label>
                    <input type="number" step="0.01" className="form-input" value={counted} onChange={(e) => setCounted(e.target.value)} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px', marginBottom: '12px', fontSize: '0.9rem' }}>
                  <div>Espèces attendues : <strong>{eur(expected)}</strong> <span style={{ color: 'var(--gray-400)', fontSize: '0.8rem' }}>(fond + espèces ± mouvements)</span></div>
                  <div style={{ color: discrepancy === 0 ? 'inherit' : 'var(--red, #ef4444)' }}>Écart : <strong>{eur(discrepancy)}</strong></div>
                </div>
                <textarea className="form-textarea" placeholder="Notes (facultatif)" value={notes} onChange={(e) => setNotes(e.target.value)} style={{ marginBottom: '12px', width: '100%' }} />
                <button className="btn btn-primary" onClick={closeDay}>Clôturer la journée</button>
              </>
            )}
          </>
        )}
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Historique des clôtures</h3>
        <div className="table-container">
          <table>
            <thead><tr><th>Date</th><th style={{ textAlign: 'right' }}>Total</th><th style={{ textAlign: 'right' }}>Attendu</th><th style={{ textAlign: 'right' }}>Compté</th><th style={{ textAlign: 'right' }}>Écart</th></tr></thead>
            <tbody>
              {closings.map((c) => (
                <tr key={c.id}>
                  <td>{c.business_date}</td>
                  <td style={{ textAlign: 'right' }}>{eur(c.total_amount)}</td>
                  <td style={{ textAlign: 'right' }}>{eur(c.expected_amount)}</td>
                  <td style={{ textAlign: 'right' }}>{eur(c.counted_amount)}</td>
                  <td style={{ textAlign: 'right', color: c.discrepancy === 0 ? 'inherit' : 'var(--red, #ef4444)' }}>{eur(c.discrepancy)}</td>
                </tr>
              ))}
              {closings.length === 0 && <tr><td colSpan="5" className="table-empty">Aucune clôture enregistrée</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '8px' }}>Export comptable</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginBottom: '12px' }}>
          Journal des ventes + trésorerie (Excel) ou fichier <strong>FEC</strong> à transmettre à ton comptable.
        </p>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Du</label>
            <input type="date" className="form-input" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Au</label>
            <input type="date" className="form-input" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <button className="btn btn-secondary" onClick={() => doExport('journal')}>Journal (Excel)</button>
          <button className="btn btn-secondary" onClick={() => doExport('fec')}>Fichier FEC</button>
        </div>
      </div>
    </div>
  );
}
