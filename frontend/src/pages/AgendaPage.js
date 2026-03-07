import React, { useState, useEffect, useCallback } from 'react';
import { appointmentsAPI, clientsAPI, animalsAPI, authAPI } from '../services/api';
import toast from 'react-hot-toast';

const typeColors = {
  consultation: '#2563eb', surgery: '#dc2626', emergency: '#f59e0b',
  vaccination: '#16a34a', checkup: '#7c3aed', grooming: '#0891b2', other: '#6b7280',
};
const typeLabels = {
  consultation: 'Consultation', surgery: 'Chirurgie', emergency: 'Urgence',
  vaccination: 'Vaccination', checkup: 'Bilan', grooming: 'Toilettage', other: 'Autre',
};

export default function AgendaPage() {
  const [appointments, setAppointments] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    client_id: '', animal_id: '', veterinarian_id: '',
    appointment_type: 'consultation', start_time: '', end_time: '', reason: '',
  });

  // Search state
  const [clientSearch, setClientSearch] = useState('');
  const [clientResults, setClientResults] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [animalOptions, setAnimalOptions] = useState([]);
  const [selectedAnimal, setSelectedAnimal] = useState(null);
  const [vets, setVets] = useState([]);

  useEffect(() => {
    async function loadVets() {
      try {
        const res = await authAPI.listUsers();
        setVets((res.data || []).filter(u => u.role === 'veterinarian' || u.role === 'admin'));
      } catch {}
    }
    loadVets();
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const res = await appointmentsAPI.list({ date_from: selectedDate, date_to: selectedDate });
        setAppointments(res.data);
      } catch { toast.error('Erreur de chargement'); }
    }
    load();
  }, [selectedDate]);

  // Client search with debounce
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
    setForm({ ...form, client_id: client.id });
    setClientSearch(`${client.last_name} ${client.first_name}`);
    setClientResults([]);
    // Load client's animals
    try {
      const res = await animalsAPI.list({ client_id: client.id });
      setAnimalOptions(res.data || []);
    } catch {}
  };

  const selectAnimal = (animal) => {
    setSelectedAnimal(animal);
    setForm({ ...form, animal_id: animal.id });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await appointmentsAPI.create({
        ...form,
        client_id: parseInt(form.client_id),
        animal_id: form.animal_id ? parseInt(form.animal_id) : null,
        veterinarian_id: parseInt(form.veterinarian_id),
      });
      toast.success('RDV cree');
      setShowForm(false);
      setSelectedClient(null);
      setSelectedAnimal(null);
      setClientSearch('');
      setAnimalOptions([]);
      const res = await appointmentsAPI.list({ date_from: selectedDate, date_to: selectedDate });
      setAppointments(res.data);
    } catch { toast.error('Erreur lors de la creation'); }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Agenda</h1>
        </div>
        <div className="page-header-actions">
          <input type="date" className="form-input" style={{ width: 'auto' }} value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Nouveau RDV</button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau rendez-vous</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group" style={{ position: 'relative' }}>
                <label className="form-label">Client *</label>
                <input
                  className="form-input"
                  placeholder="Rechercher un client..."
                  value={clientSearch}
                  onChange={(e) => { setClientSearch(e.target.value); setSelectedClient(null); setForm({ ...form, client_id: '' }); }}
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
                <label className="form-label">Animal {selectedClient ? '*' : ''}</label>
                <select className="form-select" value={form.animal_id} onChange={(e) => {
                  const a = animalOptions.find(an => an.id === parseInt(e.target.value));
                  if (a) selectAnimal(a); else { setSelectedAnimal(null); setForm({ ...form, animal_id: '' }); }
                }}>
                  <option value="">-- Choisir --</option>
                  {animalOptions.map(a => <option key={a.id} value={a.id}>{a.name} ({a.species})</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Veterinaire *</label>
                <select className="form-select" value={form.veterinarian_id} onChange={(e) => setForm({ ...form, veterinarian_id: e.target.value })} required>
                  <option value="">-- Choisir --</option>
                  {vets.map(v => <option key={v.id} value={v.id}>Dr. {v.last_name} {v.first_name}</option>)}
                </select>
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
                <label className="form-label">Debut *</label>
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
              <button type="submit" className="btn btn-primary">Creer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="agenda-legend">
        {Object.entries(typeLabels).map(([k, v]) => (
          <div key={k} className="agenda-legend-item">
            <div className="agenda-legend-dot" style={{ background: typeColors[k] }} />
            {v}
          </div>
        ))}
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>
          {new Date(selectedDate + 'T00:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </h3>
        {appointments.length === 0 ? (
          <p style={{ color: 'var(--gray-400)', textAlign: 'center' }}>Aucun RDV pour cette date</p>
        ) : (
          appointments.map((appt) => (
            <div key={appt.id} className="agenda-slot" style={{ borderLeft: `4px solid ${typeColors[appt.appointment_type] || typeColors.other}` }}>
              <div className="agenda-slot-time">
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
