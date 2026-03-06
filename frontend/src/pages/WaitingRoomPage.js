import React, { useState, useEffect } from 'react';
import { appointmentsAPI } from '../services/api';
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

  const load = async () => {
    try {
      const res = await appointmentsAPI.waitingRoom();
      setAppointments(res.data);
    } catch {
      toast.error('Erreur de chargement');
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Salle d'attente</h1>
        <button className="btn btn-secondary btn-sm" onClick={load}>Rafraîchir</button>
      </div>

      {appointments.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--gray-400)' }}>
          Personne en salle d'attente
        </div>
      ) : (
        appointments.map((appt) => (
          <div key={appt.id} className={`waiting-room-card ${appt.status.replace('_', '-')}`}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                {new Date(appt.start_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                {' - '}
                {appt.reason || appt.appointment_type}
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
                <button className="btn btn-primary btn-sm" onClick={() => updateStatus(appt.id, 'in_progress')}>
                  En consultation
                </button>
              )}
              {appt.status === 'in_progress' && (
                <button className="btn btn-success btn-sm" onClick={() => updateStatus(appt.id, 'completed')}>
                  Terminer
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
