import { queryClient } from './queryClient';
import { medicalAPI, animalsAPI } from './api';

// Enregistre la fonction de chaque mutation par clé. Indispensable pour que les
// écritures mises en file d'attente hors ligne puissent être rejouées après un
// rechargement de page : resumePausedMutations() retrouve la fonction via la
// mutationKey persistée. Appelé une fois au démarrage (index.jsx).
export function registerOfflineMutations() {
  queryClient.setMutationDefaults(['medical', 'records', 'create'], {
    mutationFn: ({ payload, idempotencyKey }) =>
      medicalAPI.createRecord(payload, idempotencyKey).then((r) => r.data),
  });
  queryClient.setMutationDefaults(['animals', 'weights', 'add'], {
    mutationFn: ({ animalId, payload, idempotencyKey }) =>
      animalsAPI.addWeight(animalId, payload, idempotencyKey).then((r) => r.data),
  });
}
