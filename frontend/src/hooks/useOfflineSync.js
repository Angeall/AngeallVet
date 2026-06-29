import { useSyncExternalStore } from 'react';
import { onlineManager, useMutationState } from '@tanstack/react-query';

// État réseau, branché sur le gestionnaire de TanStack Query (qui suit
// navigator.onLine + les événements online/offline du navigateur).
export function useOnlineStatus() {
  return useSyncExternalStore(
    (onChange) => onlineManager.subscribe(onChange),
    () => onlineManager.isOnline(),
    () => true,
  );
}

// Mutations pas encore parties sur le serveur : en attente (mises en pause hors
// ligne) ou en échec (à revérifier). Alimente le badge et le panneau
// « modifications en attente ». Les écritures fournissent un libellé lisible via
// `meta.label` au fur et à mesure de leur migration vers la file d'attente.
export function usePendingMutations() {
  return useMutationState({
    filters: {
      predicate: (m) => m.state.isPaused || m.state.status === 'error',
    },
    select: (m) => ({
      id: m.mutationId,
      label: m.options.meta?.label || 'Modification',
      status: m.state.status,
      isPaused: m.state.isPaused,
    }),
  });
}
