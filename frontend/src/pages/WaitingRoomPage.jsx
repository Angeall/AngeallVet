import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { appointmentsAPI, authAPI } from '../services/api';
import toast from 'react-hot-toast';

const statusLabels = {
  confirmed: 'Confirmé',
  arrived: 'Arrivé',
  in_progress: 'En consultation',
  completed: 'Terminé',
};

const statusColors = {
  confirmed: 'blue',
  arrived: 'amber',
  in_progress: 'green',
  completed: 'gray',
};

export default function WaitingRoomPage() {
  const [appointments, setAppointments] = useState([]);
  const [vets, setVets] = useState([]);
  const [filterVetId, setFilterVetId] = useState('');

  useEffect(() => {
    authAPI.listStaff().then(res => setVets((res.data || []).filter(u => u.role === 'veterinarian' || u.role === 'admin'))).catch(() => {});
  }, []);

  const load = async () => {
    try {
      const params = {};
      if (filterVetId) params.veterinarian_id = parseInt(filterVetId);
      const res = await appointmentsAPI.waitingRoom(params);
      setAppointments(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [filterVetId]);

  const updateStatus = async (id, status) => {
    try {
      await appointmentsAPI.updateStatus(id, { status });
      toast.success('Statut mis à jour');
      load();
    } catch {
      toast.error('Erreur');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Salle d'attente</h1>
        </div>
        <div className="page-header-actions">
          <select className="form-select" style={{ width: 'auto' }} value={filterVetId} onChange={(e) => setFilterVetId(e.target.value)}>
            <option value="">Tous les vétérinaires</option>
            {vets.map(v => <option key={v.id} value={v.id}>Dr. {v.last_name} {v.first_name}</option>)}
          </select>
          <button className="btn btn-secondary btn-sm" onClick={load}>Rafraîchir</button>
        </div>
      </div>

      {appointments.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🪑</div>
          <h3>Personne en salle d'attente</h3>
          <p>Les patients apparaîtront ici dès leur arrivée</p>
        </div>
      ) : (
        appointments.map((appt) => (
          <div key={appt.id} className={`waiting-room-card ${appt.status.replace('_', '-')}`}>
            <div className="waiting-room-info">
              <div className="waiting-room-time">
                {new Date(appt.start_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                {' - '}
                {appt.reason || appt.appointment_type}
                {appt.client_name && <span style={{ marginLeft: '8px', fontWeight: 500 }}>{appt.client_name}</span>}
                {appt.animal_name && (
                  <span style={{ marginLeft: '4px' }}>
                    (<Link to={`/animals/${appt.animal_id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }} title="Voir le dossier animal">{appt.animal_name}</Link>)
                  </span>
                )}
                {appt.veterinarian_name && <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)', marginLeft: '8px' }}>{appt.veterinarian_name}</span>}
              </div>
              <span className={`badge badge-${statusColors[appt.status]}`}>
                {statusLabels[appt.status]}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {appt.status === 'confirmed' && (
                <button className="btn btn-secondary btn-sm" onClick={() => updateStatus(appt.id, 'arrived')}>
                  Marquer arrivé
                </button>
              )}
              {appt.status === 'arrived' && (
                <>
                  <button className="btn btn-secondary btn-sm" style={{ color: 'var(--gray-500)' }} onClick={() => updateStatus(appt.id, 'scheduled')}>
                    &#8592; Planifié
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={() => updateStatus(appt.id, 'in_progress')}>
                    En consultation
                  </button>
                </>
              )}
              {appt.status === 'in_progress' && (
                <>
                  <button className="btn btn-secondary btn-sm" style={{ color: 'var(--gray-500)' }} onClick={() => updateStatus(appt.id, 'arrived')}>
                    &#8592; Arrivé
                  </button>
                  <button className="btn btn-success btn-sm" onClick={() => updateStatus(appt.id, 'completed')}>
                    Terminer
                  </button>
                </>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
