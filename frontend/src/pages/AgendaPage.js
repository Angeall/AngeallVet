import React, { useState, useEffect } from 'react';
import { appointmentsAPI, clientsAPI } from '../services/api';
import toast from 'react-hot-toast';

const typeColors = {
  consultation: '#2563eb',
  surgery: '#dc2626',
  emergency: '#f59e0b',
  vaccination: '#16a34a',
  checkup: '#7c3aed',
  grooming: '#0891b2',
  other: '#6b7280',
};

const typeLabels = {
  consultation: 'Consultation',
  surgery: 'Chirurgie',
  emergency: 'Urgence',
  vaccination: 'Vaccination',
  checkup: 'Bilan',
  grooming: 'Toilettage',
  other: 'Autre',
};

export default function AgendaPage() {
  const [appointments, setAppointments] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    client_id: '', animal_id: '', veterinarian_id: '',
    appointment_type: 'consultation', start_time: '', end_time: '', reason: '',
  });

  useEffect(() => {
    async function load() {
      try {
        const res = await appointmentsAPI.list({
          date_from: selectedDate,
          date_to: selectedDate,
        });
        setAppointments(res.data);
      } catch {
        toast.error('Erreur de chargement');
      }
    }
    load();
  }, [selectedDate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await appointmentsAPI.create({
        ...form,
        client_id: parseInt(form.client_id),
        animal_id: form.animal_id ? parseInt(form.animal_id) : null,
        veterinarian_id: parseInt(form.veterinarian_id),
      });
      toast.success('RDV créé');
      setShowForm(false);
      const res = await appointmentsAPI.list({ date_from: selectedDate, date_to: selectedDate });
      setAppointments(res.data);
    } catch {
      toast.error('Erreur lors de la création');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Agenda</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="date"
            className="form-input"
            style={{ width: 'auto' }}
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            + Nouveau RDV
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau rendez-vous</h3>
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
              <div className="form-group">
                <label className="form-label">ID Vétérinaire *</label>
                <input className="form-input" value={form.veterinarian_id} onChange={(e) => setForm({ ...form, veterinarian_id: e.target.value })} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-select" value={form.appointment_type} onChange={(e) => setForm({ ...form, appointment_type: e.target.value })}>
                  {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Début *</label>
                <input type="datetime-local" className="form-input" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Fin *</label>
                <input type="datetime-local" className="form-input" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} required />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Motif</label>
              <input className="form-input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Créer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {Object.entries(typeLabels).map(([k, v]) => (
          <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem' }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: typeColors[k] }} />
            {v}
          </div>
        ))}
      </div>

      {/* Appointment list */}
      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>
          {new Date(selectedDate + 'T00:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </h3>
        {appointments.length === 0 ? (
          <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun RDV pour cette date</p>
        ) : (
          appointments.map((appt) => (
            <div key={appt.id} style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px 16px',
              borderLeft: `4px solid ${typeColors[appt.appointment_type] || typeColors.other}`,
              borderBottom: '1px solid var(--gray-100)',
              gap: '16px',
            }}>
              <div style={{ minWidth: '100px', fontWeight: 600 }}>
                {new Date(appt.start_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                {' - '}
                {new Date(appt.end_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
              </div>
              <span className={`badge badge-${appt.status === 'completed' ? 'green' : appt.status === 'cancelled' ? 'red' : 'blue'}`}>
                {appt.status}
              </span>
              <div style={{ flex: 1 }}>
                <strong>{typeLabels[appt.appointment_type]}</strong>
                {appt.reason && <span style={{ color: 'var(--gray-500)', marginLeft: '8px' }}>- {appt.reason}</span>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
