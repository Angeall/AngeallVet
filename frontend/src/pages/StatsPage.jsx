import React, { useState, useEffect } from 'react';
import { billingAPI } from '../services/api';
import toast from 'react-hot-toast';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const periodLabels = { day: "Aujourd'hui", week: 'Cette semaine', month: 'Ce mois' };

export default function StatsPage() {
  const [period, setPeriod] = useState('day');
  const [stats, setStats] = useState(null);
  const [dateRef, setDateRef] = useState(new Date().toISOString().slice(0, 10));

  useEffect(() => {
    async function load() {
      try {
        const res = await billingAPI.getStats({ period, date_ref: dateRef });
        setStats(res.data);
      } catch {
        toast.error('Erreur de chargement des statistiques');
      }
    }
    load();
  }, [period, dateRef]);

  if (!stats) return <div className="page-content">Chargement...</div>;

  const cur = stats.current;
  const prev = stats.previous;

  const revenueChange = prev.total_revenue > 0
    ? ((cur.total_revenue - prev.total_revenue) / prev.total_revenue * 100).toFixed(1)
    : null;
  const countChange = prev.invoice_count > 0
    ? ((cur.invoice_count - prev.invoice_count) / prev.invoice_count * 100).toFixed(1)
    : null;

  // Payment method pie data
  const paymentPieData = Object.entries(stats.by_payment_method || {}).map(([method, amount]) => ({
    name: methodLabel(method), value: amount,
  }));

  // Status pie data
  const statusPieData = Object.entries(cur.by_status || {}).map(([status, amount]) => ({
    name: statusLabel(status), value: amount,
  }));

  // Daily chart data
  const dailyData = (stats.daily || []).map(d => ({
    ...d,
    label: d.date.slice(5), // MM-DD
  }));

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Statistiques</h1>
        </div>
        <div className="page-header-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="date"
            className="form-input"
            value={dateRef}
            onChange={(e) => setDateRef(e.target.value)}
            style={{ width: '160px' }}
          />
          {['day', 'week', 'month'].map(p => (
            <button
              key={p}
              className={`btn ${period === p ? 'btn-primary' : 'btn-secondary'} btn-sm`}
              onClick={() => setPeriod(p)}
            >
              {periodLabels[p]}
            </button>
          ))}
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon green">CA</div>
          <div>
            <div className="stat-value">{cur.total_revenue.toFixed(2)} EUR</div>
            <div className="stat-label">
              Chiffre d'affaires
              {revenueChange !== null && (
                <span style={{ marginLeft: '6px', color: parseFloat(revenueChange) >= 0 ? 'var(--green, #10b981)' : 'var(--red, #ef4444)', fontSize: '0.8rem' }}>
                  {parseFloat(revenueChange) >= 0 ? '+' : ''}{revenueChange}%
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue">PAY</div>
          <div>
            <div className="stat-value">{cur.total_paid.toFixed(2)} EUR</div>
            <div className="stat-label">Encaisse</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">IMP</div>
          <div>
            <div className="stat-value">{cur.total_unpaid.toFixed(2)} EUR</div>
            <div className="stat-label">Impaye</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">FAC</div>
          <div>
            <div className="stat-value">{cur.invoice_count}</div>
            <div className="stat-label">
              Factures
              {countChange !== null && (
                <span style={{ marginLeft: '6px', color: parseFloat(countChange) >= 0 ? 'var(--green, #10b981)' : 'var(--red, #ef4444)', fontSize: '0.8rem' }}>
                  {parseFloat(countChange) >= 0 ? '+' : ''}{countChange}%
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Comparison card */}
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
        {/* Daily chart */}
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

        {/* Pie charts */}
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

      {/* Fiche comptable du jour */}
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
    </div>
  );
}

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

function statusLabel(s) {
  const map = { draft: 'Brouillon', sent: 'Envoyee', paid: 'Payee', partial: 'Partielle', overdue: 'Impayee', cancelled: 'Annulee' };
  return map[s] || s;
}

function methodLabel(m) {
  const map = { cash: 'Especes', card: 'CB', check: 'Cheque', transfer: 'Virement', other: 'Autre' };
  return map[m] || m;
}
