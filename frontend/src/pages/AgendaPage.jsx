import React, { useState, useEffect } from 'react';
import { appointmentsAPI, clientsAPI, animalsAPI, authAPI, settingsAPI } from '../services/api';
import toast from 'react-hot-toast';

const typeColors = {
  consultation: '#2563eb', surgery: '#dc2626', emergency: '#f59e0b',
  vaccination: '#16a34a', checkup: '#7c3aed', grooming: '#0891b2', other: '#6b7280',
};
const typeLabels = {
  consultation: 'Consultation', surgery: 'Chirurgie', emergency: 'Urgence',
  vaccination: 'Vaccination', checkup: 'Bilan', grooming: 'Toilettage', other: 'Autre',
};
const statusLabels = {
  scheduled: 'Planifie', confirmed: 'Confirme', arrived: 'Arrive',
  in_progress: 'En cours', completed: 'Termine', cancelled: 'Annule', no_show: 'Absent',
};
const statusColors = {
  scheduled: 'blue', confirmed: 'teal', arrived: 'amber',
  in_progress: 'purple', completed: 'green', cancelled: 'red', no_show: 'gray',
};

export default function AgendaPage() {
  const [appointments, setAppointments] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [showForm, setShowForm] = useState(false);
  const [defaultDuration, setDefaultDuration] = useState(30);
  const [durationManuallySet, setDurationManuallySet] = useState(false);
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
  const [filterVetId, setFilterVetId] = useState('');

  // Quick client creation modal
  const [showClientModal, setShowClientModal] = useState(false);
  const [clientForm, setClientForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });

  // Quick animal creation modal
  const [showAnimalModal, setShowAnimalModal] = useState(false);
  const [animalForm, setAnimalForm] = useState({ name: '', species: 'dog', breed: '', sex: 'male' });

  // Edit appointment modal
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [speciesList, setSpeciesList] = useState([]);

  useEffect(() => {
    async function loadVets() {
      try {
        const res = await authAPI.listStaff();
        setVets((res.data || []).filter(u => u.role === 'veterinarian' || u.role === 'admin'));
      } catch {}
    }
    async function loadSettings() {
      try {
        const res = await settingsAPI.getClinic();
        if (res.data?.default_appointment_duration_minutes) {
          setDefaultDuration(res.data.default_appointment_duration_minutes);
        }
      } catch {}
    }
    async function loadSpecies() {
      try {
        const res = await animalsAPI.listSpecies();
        setSpeciesList(res.data || []);
      } catch {}
    }
    loadVets();
    loadSettings();
    loadSpecies();
  }, []);

  const loadAppointments = async () => {
    try {
      const params = { date_from: selectedDate, date_to: selectedDate };
      if (filterVetId) params.veterinarian_id = parseInt(filterVetId);
      const res = await appointmentsAPI.list(params);
      setAppointments(res.data);
    } catch { toast.error('Erreur de chargement'); }
  };

  useEffect(() => { loadAppointments(); }, [selectedDate, filterVetId]);

  // Auto-compute end_time when start_time changes (if not manually set)
  useEffect(() => {
    if (form.start_time && !durationManuallySet) {
      const start = new Date(form.start_time);
      start.setMinutes(start.getMinutes() + defaultDuration);
      const pad = (n) => String(n).padStart(2, '0');
      const end = `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}T${pad(start.getHours())}:${pad(start.getMinutes())}`;
      setForm(prev => ({ ...prev, end_time: end }));
    }
  }, [form.start_time, defaultDuration, durationManuallySet]);

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
    setForm(prev => ({ ...prev, client_id: client.id }));
    setClientSearch(`${client.last_name} ${client.first_name}`);
    setClientResults([]);
    try {
      const res = await animalsAPI.list({ client_id: client.id });
      setAnimalOptions(res.data || []);
    } catch {}
  };

  const selectAnimal = (animal) => {
    setSelectedAnimal(animal);
    setForm(prev => ({ ...prev, animal_id: animal.id }));
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
      setDurationManuallySet(false);
      loadAppointments();
    } catch { toast.error('Erreur lors de la creation'); }
  };

  const handleCreateClient = async (e) => {
    e.preventDefault();
    try {
      const payload = Object.fromEntries(
        Object.entries(clientForm).map(([k, v]) => [k, v === '' ? null : v])
      );
      const res = await clientsAPI.create(payload);
      toast.success('Client cree');
      setShowClientModal(false);
      setClientForm({ first_name: '', last_name: '', phone: '', email: '' });
      selectClient(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors de la creation du client');
    }
  };

  const handleCreateAnimal = async (e) => {
    e.preventDefault();
    if (!selectedClient) { toast.error('Selectionnez d\'abord un client'); return; }
    try {
      const res = await animalsAPI.create({
        ...animalForm,
        client_id: selectedClient.id,
      });
      toast.success('Animal cree');
      setShowAnimalModal(false);
      setAnimalForm({ name: '', species: 'dog', breed: '', sex: 'male' });
      // Reload animals and auto-select
      const animalsRes = await animalsAPI.list({ client_id: selectedClient.id });
      setAnimalOptions(animalsRes.data || []);
      selectAnimal(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors de la creation de l\'animal');
    }
  };

  // Appointment management
  const handleCancelAppointment = async (apptId) => {
    if (!confirm('Annuler ce rendez-vous ?')) return;
    try {
      await appointmentsAPI.cancel(apptId);
      toast.success('RDV annule');
      loadAppointments();
    } catch { toast.error('Erreur'); }
  };

  const handleStatusChange = async (apptId, status) => {
    try {
      await appointmentsAPI.updateStatus(apptId, { status });
      toast.success('Statut mis a jour');
      loadAppointments();
    } catch { toast.error('Erreur'); }
  };

  const openEditModal = (appt) => {
    setEditForm({
      id: appt.id,
      appointment_type: appt.appointment_type,
      start_time: appt.start_time?.slice(0, 16) || '',
      end_time: appt.end_time?.slice(0, 16) || '',
      reason: appt.reason || '',
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      await appointmentsAPI.update(editForm.id, {
        appointment_type: editForm.appointment_type,
        start_time: editForm.start_time,
        end_time: editForm.end_time,
        reason: editForm.reason,
      });
      toast.success('RDV modifie');
      setShowEditModal(false);
      setEditForm(null);
      loadAppointments();
    } catch { toast.error('Erreur lors de la modification'); }
  };

  const todayStr = new Date().toISOString().slice(0, 10);
  const isToday = selectedDate === todayStr;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Agenda</h1>
        </div>
        <div className="page-header-actions">
          <input type="date" className="form-input" style={{ width: 'auto' }} value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
          <select className="form-select" style={{ width: 'auto' }} value={filterVetId} onChange={(e) => setFilterVetId(e.target.value)}>
            <option value="">Tous les vétérinaires</option>
            {vets.map(v => <option key={v.id} value={v.id}>Dr. {v.last_name} {v.first_name}</option>)}
          </select>
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
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    className="form-input"
                    placeholder="Rechercher un client..."
                    value={clientSearch}
                    onChange={(e) => { setClientSearch(e.target.value); setSelectedClient(null); setForm(prev => ({ ...prev, client_id: '' })); }}
                    required={!selectedClient}
                    style={{ flex: 1 }}
                  />
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowClientModal(true)} title="Creer un nouveau client">+ Client</button>
                </div>
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
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select className="form-select" style={{ flex: 1 }} value={form.animal_id} onChange={(e) => {
                    const a = animalOptions.find(an => an.id === parseInt(e.target.value));
                    if (a) selectAnimal(a); else { setSelectedAnimal(null); setForm(prev => ({ ...prev, animal_id: '' })); }
                  }}>
                    <option value="">-- Choisir --</option>
                    {animalOptions.map(a => <option key={a.id} value={a.id}>{a.name} ({a.species})</option>)}
                  </select>
                  {selectedClient && (
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAnimalModal(true)} title="Creer un nouvel animal">+ Animal</button>
                  )}
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Veterinaire *</label>
                <select className="form-select" value={form.veterinarian_id} onChange={(e) => setForm(prev => ({ ...prev, veterinarian_id: e.target.value }))} required>
                  <option value="">-- Choisir --</option>
                  {vets.map(v => <option key={v.id} value={v.id}>Dr. {v.last_name} {v.first_name}</option>)}
                </select>
              </div>
            </div>
            {/* Client alerts */}
            {selectedClient?.alerts?.filter(a => a.is_active).length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
                {selectedClient.alerts.filter(a => a.is_active).map(alert => (
                  <div key={alert.id} className={`alert-banner ${alert.severity}`} style={{ margin: 0, padding: '6px 12px', fontSize: '0.85rem' }}>
                    <strong>Client - {alert.alert_type}:</strong> {alert.message}
                  </div>
                ))}
              </div>
            )}
            {/* Animal alerts */}
            {selectedAnimal?.alerts?.filter(a => a.is_active).length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
                {selectedAnimal.alerts.filter(a => a.is_active).map(alert => (
                  <div key={alert.id} className={`alert-banner ${alert.severity}`} style={{ margin: 0, padding: '6px 12px', fontSize: '0.85rem' }}>
                    <strong>{selectedAnimal.name} - {alert.alert_type}:</strong> {alert.message}
                  </div>
                ))}
              </div>
            )}

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-select" value={form.appointment_type} onChange={(e) => setForm(prev => ({ ...prev, appointment_type: e.target.value }))}>
                  {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Debut *</label>
                <input type="datetime-local" className="form-input" value={form.start_time} onChange={(e) => { setDurationManuallySet(false); setForm(prev => ({ ...prev, start_time: e.target.value })); }} required />
              </div>
              <div className="form-group">
                <label className="form-label">Fin * <span style={{ fontSize: '0.75rem', color: 'var(--gray-400)' }}>({defaultDuration} min par defaut)</span></label>
                <input type="datetime-local" className="form-input" value={form.end_time} onChange={(e) => { setDurationManuallySet(true); setForm(prev => ({ ...prev, end_time: e.target.value })); }} required />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Motif</label>
              <input className="form-input" value={form.reason} onChange={(e) => setForm(prev => ({ ...prev, reason: e.target.value }))} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary">Creer</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Annuler</button>
            </div>
          </form>
        </div>
      )}

      {/* Quick client creation modal */}
      {showClientModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={(e) => { if (e.target === e.currentTarget) setShowClientModal(false); }}>
          <div className="card" style={{ width: '480px', maxWidth: '90vw', margin: 0 }}>
            <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouveau client</h3>
            <form onSubmit={handleCreateClient}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Prenom *</label>
                  <input className="form-input" value={clientForm.first_name} onChange={(e) => setClientForm({ ...clientForm, first_name: e.target.value })} required autoFocus />
                </div>
                <div className="form-group">
                  <label className="form-label">Nom *</label>
                  <input className="form-input" value={clientForm.last_name} onChange={(e) => setClientForm({ ...clientForm, last_name: e.target.value })} required />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Telephone</label>
                  <input className="form-input" value={clientForm.phone} onChange={(e) => setClientForm({ ...clientForm, phone: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input type="email" className="form-input" value={clientForm.email} onChange={(e) => setClientForm({ ...clientForm, email: e.target.value })} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowClientModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary">Creer et selectionner</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Quick animal creation modal */}
      {showAnimalModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={(e) => { if (e.target === e.currentTarget) setShowAnimalModal(false); }}>
          <div className="card" style={{ width: '480px', maxWidth: '90vw', margin: 0 }}>
            <h3 className="card-title" style={{ marginBottom: '16px' }}>Nouvel animal pour {selectedClient?.last_name} {selectedClient?.first_name}</h3>
            <form onSubmit={handleCreateAnimal}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Nom *</label>
                  <input className="form-input" value={animalForm.name} onChange={(e) => setAnimalForm({ ...animalForm, name: e.target.value })} required autoFocus />
                </div>
                <div className="form-group">
                  <label className="form-label">Espece *</label>
                  <select className="form-select" value={animalForm.species} onChange={(e) => setAnimalForm({ ...animalForm, species: e.target.value })}>
                    {speciesList.map(s => <option key={s.code} value={s.code}>{s.label}</option>)}
                    {speciesList.length === 0 && <option value="dog">Chien</option>}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Race</label>
                  <input className="form-input" value={animalForm.breed} onChange={(e) => setAnimalForm({ ...animalForm, breed: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Sexe</label>
                  <select className="form-select" value={animalForm.sex} onChange={(e) => setAnimalForm({ ...animalForm, sex: e.target.value })}>
                    <option value="male">Male</option>
                    <option value="female">Femelle</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAnimalModal(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary">Creer et selectionner</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit appointment modal */}
      {showEditModal && editForm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={(e) => { if (e.target === e.currentTarget) { setShowEditModal(false); setEditForm(null); } }}>
          <div className="card" style={{ width: '540px', maxWidth: '90vw', margin: 0 }}>
            <h3 className="card-title" style={{ marginBottom: '16px' }}>Modifier le rendez-vous</h3>
            <form onSubmit={handleEditSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Type</label>
                  <select className="form-select" value={editForm.appointment_type} onChange={(e) => setEditForm({ ...editForm, appointment_type: e.target.value })}>
                    {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Debut *</label>
                  <input type="datetime-local" className="form-input" value={editForm.start_time} onChange={(e) => setEditForm({ ...editForm, start_time: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Fin *</label>
                  <input type="datetime-local" className="form-input" value={editForm.end_time} onChange={(e) => setEditForm({ ...editForm, end_time: e.target.value })} required />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Motif</label>
                <input className="form-input" value={editForm.reason} onChange={(e) => setEditForm({ ...editForm, reason: e.target.value })} />
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setShowEditModal(false); setEditForm(null); }}>Annuler</button>
                <button type="submit" className="btn btn-primary">Enregistrer</button>
              </div>
            </form>
          </div>
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
              <span className={`badge badge-${statusColors[appt.status] || 'blue'}`}>
                {statusLabels[appt.status] || appt.status}
              </span>
              <div style={{ flex: 1 }}>
                <strong>{typeLabels[appt.appointment_type]}</strong>
                {appt.client_name && <span style={{ marginLeft: '8px' }}>{appt.client_name}</span>}
                {appt.animal_name && <span style={{ color: 'var(--gray-500)', marginLeft: '4px' }}>({appt.animal_name})</span>}
                {appt.reason && <span style={{ color: 'var(--gray-500)', marginLeft: '8px' }}>- {appt.reason}</span>}
                {appt.veterinarian_name && <div style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{appt.veterinarian_name}</div>}
              </div>
              {/* Action buttons */}
              {appt.status !== 'cancelled' && appt.status !== 'completed' && (
                <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                  {isToday && appt.status === 'scheduled' && (
                    <button className="btn btn-sm" style={{ background: 'var(--teal-50)', color: 'var(--teal-700)', border: '1px solid var(--teal-200)' }} onClick={() => handleStatusChange(appt.id, 'arrived')} title="Client arrive">
                      Arrive
                    </button>
                  )}
                  {isToday && appt.status === 'arrived' && (
                    <>
                      <button className="btn btn-sm" style={{ background: 'var(--gray-50)', color: 'var(--gray-600)', border: '1px solid var(--gray-200)' }} onClick={() => handleStatusChange(appt.id, 'scheduled')} title="Remettre en planifie">
                        &#8592; Planifie
                      </button>
                      <button className="btn btn-sm" style={{ background: 'var(--purple-50)', color: 'var(--purple-700)', border: '1px solid var(--purple-200)' }} onClick={() => handleStatusChange(appt.id, 'in_progress')} title="Demarrer la consultation">
                        Demarrer
                      </button>
                    </>
                  )}
                  {isToday && appt.status === 'in_progress' && (
                    <>
                      <button className="btn btn-sm" style={{ background: 'var(--gray-50)', color: 'var(--gray-600)', border: '1px solid var(--gray-200)' }} onClick={() => handleStatusChange(appt.id, 'arrived')} title="Remettre en salle d'attente">
                        &#8592; Arrive
                      </button>
                      <button className="btn btn-sm" style={{ background: 'var(--green-50)', color: 'var(--green-700)', border: '1px solid var(--green-200)' }} onClick={() => handleStatusChange(appt.id, 'completed')} title="Terminer">
                        Terminer
                      </button>
                    </>
                  )}
                  <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(appt)} title="Modifier">
                    Modifier
                  </button>
                  <button className="btn btn-secondary btn-sm" style={{ color: 'var(--danger)' }} onClick={() => handleCancelAppointment(appt.id)} title="Annuler">
                    Annuler
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
