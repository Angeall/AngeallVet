import { useMutation, useQueryClient, onlineManager } from '@tanstack/react-query';
import toast from 'react-hot-toast';

// Cœur réutilisable pour une écriture durable hors ligne :
// - clé d'idempotence (UUID) ajoutée à chaque appel, stable pour le rejeu ;
// - libellé pour le panneau « modifications en attente » (meta.label) ;
// - mise à jour optimiste optionnelle du cache + rollback si échec ;
// - revalidation au succès quand on est en ligne.
//
// La fonction d'envoi elle-même est enregistrée par clé dans
// services/mutations.js, pour pouvoir reprendre après un rechargement de page.
export function useOfflineMutation({
  mutationKey,
  label,
  queryKey,
  applyOptimistic,
  successMessage,
  offlineMessage,
}) {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationKey,
    meta: label ? { label } : undefined,
    onMutate: async (variables) => {
      if (!queryKey || !applyOptimistic) return {};
      await qc.cancelQueries({ queryKey });
      const prev = qc.getQueryData(queryKey);
      qc.setQueryData(queryKey, (old) => applyOptimistic(old, variables));
      return { prev };
    },
    onError: (err, _variables, ctx) => {
      if (queryKey && ctx && 'prev' in ctx) qc.setQueryData(queryKey, ctx.prev);
      toast.error(err?.response?.data?.detail || 'Erreur');
    },
    onSuccess: () => {
      if (successMessage) toast.success(successMessage);
      if (queryKey && onlineManager.isOnline()) qc.invalidateQueries({ queryKey });
    },
  });

  const run = (variables = {}) => {
    mutation.mutate({ ...variables, idempotencyKey: crypto.randomUUID() });
    if (!onlineManager.isOnline() && offlineMessage) toast(offlineMessage, { icon: '📴' });
  };

  return { run, isPending: mutation.isPending };
}
