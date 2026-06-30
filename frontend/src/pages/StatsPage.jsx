import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { billingAPI, authAPI, commissionsAPI, exportsAPI } from '../services/api';
import { downloadBlob } from '../services/download';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const periodLabels = { day: "Aujourd'hui", week: 'Cette semaine', month: 'Ce mois' };
const statusLabelMap = { draft: 'Brouillon', sent: 'Envoyee', paid: 'Payee', partial: 'Partielle', overdue: 'Impayee', cancelled: 'Annulee' };
const statusColorMap = { draft: 'gray', sent: 'blue', paid: 'green', partial: 'amber', overdue: 'red', cancelled: 'gray' };

export default function StatsPage() {
  const [tab, setTab] = useState('global');
  const [period, setPeriod] = useState('day');
  const [stats, setStats] = useState(null);
  const [dateRef, setDateRef] = useState(new Date().toISOString().slice(0, 10));

  // Vet invoice view state
  const [vets, setVets] = useState([]);
  const [selectedVetId, setSelectedVetId] = useState('');
  const [vetDateFrom, setVetDateFrom] = useState(() => {
    const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10);
  });
  const [vetDateTo, setVetDateTo] = useState(new Date().toISOString().slice(0, 10));
  const [vetInvoices, setVetInvoices] = useState([]);
  const [vetLoading, setVetLoading] = useState(false);
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [commissions, setCommissions] = useState(null);
  const [rules, setRules] = useState([]);

  useEffect(() => {
    authAPI.listStaff().then(res => {
      setVets((res.data || []).filter(u => u.role === 'veterinarian' || u.role === 'admin'));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab !== 'global') return;
    async function load() {
      try {
        const res = await billingAPI.getStats({ period, date_ref: dateRef });
        setStats(res.data);
      } catch {
        toast.error('Erreur de chargement des statistiques');
      }
    }
    load();
  }, [period, dateRef, tab]);

  const loadVetInvoices = async () => {
    setVetLoading(true);
    try {
      const params = { date_from: vetDateFrom, date_to: vetDateTo, limit: 500 };
      if (selectedVetId) params.veterinarian_id = parseInt(selectedVetId);
      const res = await billingAPI.listInvoices(params);
      setVetInvoices(res.data || []);
    } catch {
      toast.error('Erreur de chargement');
    } finally {
      setVetLoading(false);
    }
  };

  const loadCommissions = async () => {
    if (!isAdmin) return;
    try {
      const params = { date_from: vetDateFrom, date_to: vetDateTo };
      if (selectedVetId) params.veterinarian_id = parseInt(selectedVetId);
      const [c, r] = await Promise.all([commissionsAPI.report(params), commissionsAPI.listRules()]);
      setCommissions(c.data);
      setRules((r.data || []).filter((x) => x.is_active));
    } catch { /* admin uniquement ; ignoré pour les autres rôles */ }
  };

  const changeDayRule = async (userId, dateStr, ruleId) => {
    try {
      await commissionsAPI.setDayRule({ user_id: userId, date: dateStr, rule_id: ruleId ? parseInt(ruleId) : null });
      loadCommissions();
    } catch { toast.error('Erreur'); }
  };

  useEffect(() => {
    if (tab === 'vet') { loadVetInvoices(); loadCommissions(); }
  }, [tab, selectedVetId, vetDateFrom, vetDateTo]);

  // Vet summary
  const vetTotal = vetInvoices.reduce((s, inv) => s + parseFloat(inv.total || 0), 0);
  const vetPaid = vetInvoices.reduce((s, inv) => s + parseFloat(inv.amount_paid || 0), 0);
  const vetUnpaid = vetTotal - vetPaid;
  const vetPaidCount = vetInvoices.filter(inv => inv.status === 'paid').length;

  const exportGlobal = async () => {
    if (!stats) return;
    const sheets = [
      { title: 'Synthese', headers: ['Indicateur', 'Periode', 'Precedent'], rows: [
        ['CA TTC', stats.current.total_revenue, stats.previous.total_revenue],
        ['Encaisse', stats.current.total_paid, stats.previous.total_paid],
        ['Impaye', stats.current.total_unpaid, stats.previous.total_unpaid],
        ['Factures', stats.current.invoice_count, stats.previous.invoice_count],
        ['Factures payees', stats.current.paid_count, stats.previous.paid_count],
      ] },
      { title: 'Par jour', headers: ['Date', 'CA', 'Encaisse', 'Factures'], rows: (stats.daily || []).map(d => [d.date, d.revenue, d.paid, d.count]) },
      { title: 'Par statut', headers: ['Statut', 'Montant'], rows: Object.entries(stats.current.by_status || {}).map(([k, v]) => [statusLabelMap[k] || k, v]) },
      { title: 'Modes de paiement', headers: ['Mode', 'Montant'], rows: Object.entries(stats.by_payment_method || {}).map(([k, v]) => [methodLabel(k), v]) },
    ];
    try { downloadBlob(await exportsAPI.xlsx({ filename: `stats_${stats.start}_${stats.end}`, sheets }), 'stats.xlsx'); }
    catch { toast.error('Erreur lors de l\'export'); }
  };

  const exportVet = async () => {
    const sheets = [
      { title: 'Factures', headers: ['N', 'Date', 'Client', 'Veterinaires', 'Total TTC', 'Paye', 'Statut'], rows: vetInvoices.map(inv => [
        inv.invoice_number, inv.issue_date, inv.client_name || '',
        (inv.veterinarians || []).map(v => v.user_name || `#${v.user_id}`).join(', '),
        parseFloat(inv.total || 0), parseFloat(inv.amount_paid || 0), statusLabelMap[inv.status] || inv.status,
      ]) },
    ];
    if (isAdmin && commissions) {
      sheets.push({ title: 'Commissions', headers: ['Veterinaire', 'Encaisse', 'Commission'], rows: commissions.veterinarians.map(v => [v.name, v.paid, v.commission]) });
      const detail = [];
      commissions.veterinarians.forEach(v => v.by_day.forEach(d => detail.push([v.name, d.date, d.rule_name || '', d.paid, d.commission])));
      sheets.push({ title: 'Commissions par jour', headers: ['Veterinaire', 'Jour', 'Regle', 'Encaisse', 'Commission'], rows: detail });
    }
    try { downloadBlob(await exportsAPI.xlsx({ filename: `facturation_${vetDateFrom}_${vetDateTo}`, sheets }), 'facturation.xlsx'); }
    catch { toast.error('Erreur lors de l\'export'); }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Statistiques</h1>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'global' ? 'tab active' : 'tab'} onClick={() => setTab('global')}>Vue globale</button>
        <button className={tab === 'vet' ? 'tab active' : 'tab'} onClick={() => setTab('vet')}>Facturation veterinaire</button>
      </div>

      {/* ==================== GLOBAL TAB ==================== */}
      {tab === 'global' && (
        <div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
            <input type="date" className="form-input" value={dateRef} onChange={(e) => setDateRef(e.target.value)} style={{ width: '160px' }} />
            {['day', 'week', 'month'].map(p => (
              <button key={p} className={`btn ${period === p ? 'btn-primary' : 'btn-secondary'} btn-sm`} onClick={() => setPeriod(p)}>
                {periodLabels[p]}
              </button>
            ))}
            <button className="btn btn-secondary btn-sm" style={{ marginLeft: 'auto' }} onClick={exportGlobal}>Exporter Excel</button>
          </div>

          {!stats ? <p>Chargement...</p> : <GlobalStatsView stats={stats} />}
        </div>
      )}

      {/* ==================== VET TAB ==================== */}
      {tab === 'vet' && (
        <div>
          {/* Filters */}
          <div className="card" style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Veterinaire</label>
                <select className="form-select" value={selectedVetId} onChange={(e) => setSelectedVetId(e.target.value)} style={{ minWidth: '200px' }}>
                  <option value="">Tous les veterinaires</option>
                  {vets.map(v => <option key={v.id} value={v.id}>Dr. {v.last_name} {v.first_name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Du</label>
                <input type="date" className="form-input" value={vetDateFrom} onChange={(e) => setVetDateFrom(e.target.value)} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Au</label>
                <input type="date" className="form-input" value={vetDateTo} onChange={(e) => setVetDateTo(e.target.value)} />
              </div>
              <button className="btn btn-secondary" style={{ marginLeft: 'auto' }} onClick={exportVet}>Exporter Excel</button>
            </div>
          </div>

          {/* Summary cards */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon green">CA</div>
              <div><div className="stat-value">{vetTotal.toFixed(2)} EUR</div><div className="stat-label">Chiffre d'affaires</div></div>
            </div>
            <div className="stat-card">
              <div className="stat-icon blue">PAY</div>
              <div><div className="stat-value">{vetPaid.toFixed(2)} EUR</div><div className="stat-label">Encaisse</div></div>
            </div>
            <div className="stat-card">
              <div className="stat-icon red">IMP</div>
              <div><div className="stat-value">{vetUnpaid.toFixed(2)} EUR</div><div className="stat-label">Impaye</div></div>
            </div>
            <div className="stat-card">
              <div className="stat-icon amber">FAC</div>
              <div><div className="stat-value">{vetInvoices.length} ({vetPaidCount} payees)</div><div className="stat-label">Factures</div></div>
            </div>
          </div>

          {isAdmin && commissions && (
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: '16px' }}>Commissions a payer <span style={{ fontWeight: 400, fontSize: '0.85rem', color: 'var(--gray-400)' }}>(sur l'encaisse)</span></h3>
              {commissions.veterinarians.length === 0 ? (
                <p style={{ textAlign: 'center', color: 'var(--gray-400)' }}>Aucun encaissement sur la periode</p>
              ) : (
                commissions.veterinarians.map((v) => (
                  <div key={v.user_id} style={{ marginBottom: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                      <strong>{v.name}</strong>
                      <span>
                        <span style={{ color: 'var(--gray-400)', marginRight: '10px', fontSize: '0.85rem' }}>encaisse {v.paid.toFixed(2)} EUR</span>
                        <span style={{ fontWeight: 700, color: 'var(--primary)' }}>{v.commission.toFixed(2)} EUR</span>
                      </span>
                    </div>
                    <table>
                      <thead><tr><th>Jour</th><th>Encaisse</th><th>Regle appliquee ce jour</th><th style={{ textAlign: 'right' }}>Commission</th></tr></thead>
                      <tbody>
                        {v.by_day.map((d) => (
                          <tr key={d.date}>
                            <td>{d.date}</td>
                            <td>{d.paid.toFixed(2)} EUR</td>
                            <td>
                              <select className="form-select" style={{ maxWidth: '220px' }} value={d.rule_id || ''} onChange={(e) => changeDayRule(v.user_id, d.date, e.target.value)}>
                                <option value="">Par defaut (programme)</option>
                                {rules.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                              </select>
                            </td>
                            <td style={{ textAlign: 'right', fontWeight: 600 }}>{d.commission.toFixed(2)} EUR</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Invoice list */}
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: '16px' }}>
              {selectedVetId ? `Factures - Dr. ${vets.find(v => v.id === parseInt(selectedVetId))?.last_name || ''}` : 'Toutes les factures'}
              <span style={{ fontWeight: 400, fontSize: '0.85rem', color: 'var(--gray-400)', marginLeft: '8px' }}>
                ({vetDateFrom} au {vetDateTo})
              </span>
            </h3>
            {vetLoading ? (
              <p style={{ textAlign: 'center', color: 'var(--gray-400)' }}>Chargement...</p>
            ) : vetInvoices.length === 0 ? (
              <p style={{ textAlign: 'center', color: 'var(--gray-400)' }}>Aucune facture pour cette periode</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>N</th>
                    <th>Date</th>
                    <th>Client</th>
                    <th>Veterinaire(s)</th>
                    <th>Total TTC</th>
                    <th>Paye</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {vetInvoices.map(inv => {
                    const vetNames = (inv.veterinarians || []).map(v => v.user_name || `#${v.user_id}`);
                    const isShared = vetNames.length > 1;
                    return (
                      <tr key={inv.id}>
                        <td><Link to={`/invoices/${inv.id}`} className="table-link">{inv.invoice_number}</Link></td>
                        <td>{inv.issue_date}</td>
                        <td>{inv.client_name || '-'}</td>
                        <td>
                          {vetNames.map((name, i) => (
                            <span key={i}>
                              {i > 0 && ', '}
                              <span style={isShared ? { fontWeight: 600, color: 'var(--primary)' } : {}}>{name}</span>
                            </span>
                          ))}
                          {isShared && <span className="badge badge-purple" style={{ marginLeft: '6px', fontSize: '0.7rem' }}>Partagee</span>}
                        </td>
                        <td style={{ fontWeight: 600 }}>{parseFloat(inv.total || 0).toFixed(2)} EUR</td>
                        <td>{parseFloat(inv.amount_paid || 0).toFixed(2)} EUR</td>
                        <td><span className={`badge badge-${statusColorMap[inv.status] || 'gray'}`}>{statusLabelMap[inv.status] || inv.status}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 700, borderTop: '2px solid var(--gray-200)' }}>
                    <td colSpan="4" style={{ textAlign: 'right' }}>Total</td>
                    <td>{vetTotal.toFixed(2)} EUR</td>
                    <td>{vetPaid.toFixed(2)} EUR</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


/* ==================== GLOBAL STATS SUB-COMPONENT ==================== */
function GlobalStatsView({ stats }) {
  const cur = stats.current;
  const prev = stats.previous;

  const revenueChange = prev.total_revenue > 0
    ? ((cur.total_revenue - prev.total_revenue) / prev.total_revenue * 100).toFixed(1)
    : null;
  const countChange = prev.invoice_count > 0
    ? ((cur.invoice_count - prev.invoice_count) / prev.invoice_count * 100).toFixed(1)
    : null;

  const paymentPieData = Object.entries(stats.by_payment_method || {}).map(([method, amount]) => ({
    name: methodLabel(method), value: amount,
  }));
  const statusPieData = Object.entries(cur.by_status || {}).map(([status, amount]) => ({
    name: statusLabelMap[status] || status, value: amount,
  }));
  const dailyData = (stats.daily || []).map(d => ({ ...d, label: d.date.slice(5) }));

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon green">CA</div>
          <div>
            <div className="stat-value">{cur.total_revenue.toFixed(2)} EUR</div>
            <div className="stat-label">
              Chiffre d'affaires
              {revenueChange !== null && (
                <span style={{ marginLeft: '6px', color: parseFloat(revenueChange) >= 0 ? '#10b981' : '#ef4444', fontSize: '0.8rem' }}>
                  {parseFloat(revenueChange) >= 0 ? '+' : ''}{revenueChange}%
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">PAY</div>
          <div><div className="stat-value">{cur.total_paid.toFixed(2)} EUR</div><div className="stat-label">Encaisse</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">IMP</div>
          <div><div className="stat-value">{cur.total_unpaid.toFixed(2)} EUR</div><div className="stat-label">Impaye</div></div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">FAC</div>
          <div>
            <div className="stat-value">{cur.invoice_count}</div>
            <div className="stat-label">
              Factures
              {countChange !== null && (
                <span style={{ marginLeft: '6px', color: parseFloat(countChange) >= 0 ? '#10b981' : '#ef4444', fontSize: '0.8rem' }}>
                  {parseFloat(countChange) >= 0 ? '+' : ''}{countChange}%
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Comparaison avec la periode precedente</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <CompareBlock label="CA" current={cur.total_revenue} previous={prev.total_revenue} unit=" EUR" />
          <CompareBlock label="Encaisse" current={cur.total_paid} previous={prev.total_paid} unit=" EUR" />
          <CompareBlock label="Factures" current={cur.invoice_count} previous={prev.invoice_count} unit="" />
          <CompareBlock label="Factures payees" current={cur.paid_count} previous={prev.paid_count} unit="" />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px' }}>
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Evolution du CA</h3>
          {dailyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip formatter={(v) => `${v.toFixed(2)} EUR`} />
                <Bar dataKey="revenue" name="CA" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="paid" name="Encaisse" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--gray-400)' }}>Pas de donnees</p>
          )}
        </div>

        <div>
          {statusPieData.length > 0 && (
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: '16px' }}>Repartition par statut</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={statusPieData} cx="50%" cy="50%" outerRadius={70} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {statusPieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={v => `${v.toFixed(2)} EUR`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {paymentPieData.length > 0 && (
            <div className="card" style={{ marginTop: '16px' }}>
              <h3 className="card-title" style={{ marginBottom: '16px' }}>Modes de paiement</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={paymentPieData} cx="50%" cy="50%" outerRadius={70} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {paymentPieData.map((_, i) => <Cell key={i} fill={COLORS[(i + 2) % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={v => `${v.toFixed(2)} EUR`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '16px' }}>
        <h3 className="card-title" style={{ marginBottom: '16px' }}>Fiche comptable - {stats.start === stats.end ? stats.start : `${stats.start} au ${stats.end}`}</h3>
        <table>
          <thead>
            <tr><th>Indicateur</th><th>Periode actuelle</th><th>Periode precedente</th><th>Variation</th></tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Chiffre d'affaires TTC</strong></td>
              <td>{cur.total_revenue.toFixed(2)} EUR</td>
              <td>{prev.total_revenue.toFixed(2)} EUR</td>
              <td>{variationBadge(cur.total_revenue, prev.total_revenue)}</td>
            </tr>
            <tr>
              <td><strong>Montant encaisse</strong></td>
              <td>{cur.total_paid.toFixed(2)} EUR</td>
              <td>{prev.total_paid.toFixed(2)} EUR</td>
              <td>{variationBadge(cur.total_paid, prev.total_paid)}</td>
            </tr>
            <tr>
              <td><strong>Montant impaye</strong></td>
              <td>{cur.total_unpaid.toFixed(2)} EUR</td>
              <td>{prev.total_unpaid.toFixed(2)} EUR</td>
              <td>{variationBadge(cur.total_unpaid, prev.total_unpaid, true)}</td>
            </tr>
            <tr>
              <td><strong>Nombre de factures</strong></td>
              <td>{cur.invoice_count}</td>
              <td>{prev.invoice_count}</td>
              <td>{variationBadge(cur.invoice_count, prev.invoice_count)}</td>
            </tr>
            <tr>
              <td><strong>Factures payees</strong></td>
              <td>{cur.paid_count}</td>
              <td>{prev.paid_count}</td>
              <td>{variationBadge(cur.paid_count, prev.paid_count)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </>
  );
}


/* ==================== HELPERS ==================== */
function CompareBlock({ label, current, previous, unit }) {
  const diff = previous > 0 ? ((current - previous) / previous * 100).toFixed(1) : null;
  const isUp = parseFloat(diff) >= 0;
  return (
    <div style={{ padding: '12px', border: '1px solid var(--gray-100)', borderRadius: '8px' }}>
      <div style={{ fontSize: '0.8rem', color: 'var(--gray-500)' }}>{label}</div>
      <div style={{ fontSize: '1.3rem', fontWeight: 700 }}>{typeof current === 'number' && unit === ' EUR' ? current.toFixed(2) : current}{unit}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)' }}>
        Avant: {typeof previous === 'number' && unit === ' EUR' ? previous.toFixed(2) : previous}{unit}
        {diff !== null && (
          <span style={{ marginLeft: '6px', color: isUp ? '#10b981' : '#ef4444', fontWeight: 600 }}>
            {isUp ? '+' : ''}{diff}%
          </span>
        )}
      </div>
    </div>
  );
}

function variationBadge(current, previous, invertColor = false) {
  if (previous === 0 && current === 0) return <span className="badge badge-gray">-</span>;
  if (previous === 0) return <span className="badge badge-green">Nouveau</span>;
  const pct = ((current - previous) / previous * 100).toFixed(1);
  const isUp = parseFloat(pct) >= 0;
  const color = invertColor ? (isUp ? 'red' : 'green') : (isUp ? 'green' : 'red');
  return <span className={`badge badge-${color}`}>{isUp ? '+' : ''}{pct}%</span>;
}

function methodLabel(m) {
  const map = { cash: 'Especes', card: 'CB', check: 'Cheque', transfer: 'Virement', other: 'Autre' };
  return map[m] || m;
}
