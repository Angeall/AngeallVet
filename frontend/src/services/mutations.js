import { queryClient } from './queryClient';
import { medicalAPI, animalsAPI, appointmentsAPI, clientsAPI, hospitalizationAPI } from './api';

// Enregistre la fonction d'envoi de chaque mutation par clé. Indispensable pour
// que les écritures mises en file d'attente hors ligne puissent être rejouées
// après un rechargement (resumePausedMutations retrouve la fonction via la
// mutationKey persistée). Appelé une fois au démarrage (index.jsx).
//
// Seules les créations portent une clé d'idempotence : les mises à jour / statuts
// / annulations sont naturellement idempotentes (rejouer un PUT/PATCH/DELETE
// donne le même état).
export function registerOfflineMutations() {
  // Consultation (fiche animal)
  queryClient.setMutationDefaults(['medical', 'records', 'create'], {
    mutationFn: ({ payload, idempotencyKey }) => medicalAPI.createRecord(payload, idempotencyKey).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['animals', 'weights', 'add'], {
    mutationFn: ({ animalId, payload, idempotencyKey }) => animalsAPI.addWeight(animalId, payload, idempotencyKey).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['animals', 'update'], {
    mutationFn: ({ id, payload }) => animalsAPI.update(id, payload).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['animals', 'alerts', 'add'], {
    mutationFn: ({ id, payload, idempotencyKey }) => animalsAPI.addAlert(id, payload, idempotencyKey).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['animals', 'alerts', 'remove'], {
    mutationFn: ({ id, alertId }) => animalsAPI.removeAlert(id, alertId).then((r) => r.data),
  });

  // Hospitalisation
  queryClient.setMutationDefaults(['hospitalization', 'create'], {
    mutationFn: ({ payload, idempotencyKey }) => hospitalizationAPI.create(payload, idempotencyKey).then((r) => r.data),
  });

  // Rendez-vous (agenda)
  queryClient.setMutationDefaults(['appointments', 'create'], {
    mutationFn: ({ payload, idempotencyKey }) => appointmentsAPI.create(payload, idempotencyKey).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['appointments', 'update'], {
    mutationFn: ({ id, payload }) => appointmentsAPI.update(id, payload).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['appointments', 'status'], {
    mutationFn: ({ id, status }) => appointmentsAPI.updateStatus(id, { status }).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['appointments', 'cancel'], {
    mutationFn: ({ id }) => appointmentsAPI.cancel(id).then((r) => r.data),
  });

  // Clients
  queryClient.setMutationDefaults(['clients', 'create'], {
    mutationFn: ({ payload, idempotencyKey }) => clientsAPI.create(payload, idempotencyKey).then((r) => r.data),
  });
}
