import { useQuery, useMutation, useQueryClient, onlineManager } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { animalsAPI, medicalAPI, hospitalizationAPI, appointmentsAPI } from '../services/api';

export function animalDetailKey(id) {
  return ['animalDetail', String(id)];
}

// Charge tout le dossier de l'animal en une requête. Le résultat est mis en
// cache (mémoire + IndexedDB) et donc resservi hors ligne pendant la
// consultation en cours.
export function useAnimalDetail(id) {
  return useQuery({
    queryKey: animalDetailKey(id),
    enabled: !!id,
    queryFn: async () => {
      const [a, w, r, t, h, appt] = await Promise.all([
        animalsAPI.get(id),
        animalsAPI.getWeights(id),
        medicalAPI.listRecords({ animal_id: id }),
        medicalAPI.listTemplates({}),
        hospitalizationAPI.list({ animal_id: id }),
        appointmentsAPI.list({ animal_id: id }),
      ]);
      return {
        animal: a.data,
        weights: w.data,
        records: r.data,
        templates: t.data,
        hospitalizations: h.data,
        appointments: appt.data,
      };
    },
  });
}

// Création d'un dossier médical, durable hors ligne : mise à jour optimiste du
// cache (le dossier apparaît tout de suite), mise en file d'attente sans réseau,
// idempotence côté serveur via une clé stable.
export function useCreateMedicalRecord(id, animalName) {
  const qc = useQueryClient();
  const key = animalDetailKey(id);
  const mutation = useMutation({
    mutationKey: ['medical', 'records', 'create'],
    meta: { label: animalName ? `Consultation — ${animalName}` : 'Consultation' },
    onMutate: async ({ optimisticRecord, payload }) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData(key);
      const now = new Date().toISOString();
      qc.setQueryData(key, (old) => {
        if (!old) return old;
        return {
          ...old,
          records: optimisticRecord ? [optimisticRecord, ...old.records] : old.records,
          weights:
            payload.weight_kg != null
              ? [{ id: `tmp-w-${optimisticRecord?.id || now}`, weight_kg: payload.weight_kg, recorded_at: now, __optimistic: true }, ...old.weights]
              : old.weights,
        };
      });
      return { prev };
    },
    onError: (err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
      toast.error(err?.response?.data?.detail || 'Erreur lors de la création');
    },
    onSuccess: () => {
      toast.success('Dossier médical enregistré');
      if (onlineManager.isOnline()) qc.invalidateQueries({ queryKey: key });
    },
  });

  const submitRecord = (payload, optimisticRecord) => {
    mutation.mutate({ payload, optimisticRecord, idempotencyKey: crypto.randomUUID() });
    if (!onlineManager.isOnline()) {
      toast('Enregistré localement — synchronisation en attente', { icon: '📴' });
    }
  };

  return { submitRecord, isSaving: mutation.isPending };
}

// Ajout d'une pesée, même logique offline-first que la création de dossier.
export function useAddWeight(id, animalName) {
  const qc = useQueryClient();
  const key = animalDetailKey(id);
  const mutation = useMutation({
    mutationKey: ['animals', 'weights', 'add'],
    meta: { label: animalName ? `Pesée — ${animalName}` : 'Pesée' },
    onMutate: async ({ payload, idempotencyKey }) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData(key);
      const now = new Date().toISOString();
      qc.setQueryData(key, (old) =>
        old
          ? { ...old, weights: [{ id: `tmp-w-${idempotencyKey}`, weight_kg: payload.weight_kg, recorded_at: now, __optimistic: true }, ...old.weights] }
          : old,
      );
      return { prev };
    },
    onError: (err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
      toast.error('Erreur');
    },
    onSuccess: () => {
      toast.success('Poids enregistré');
      if (onlineManager.isOnline()) qc.invalidateQueries({ queryKey: key });
    },
  });

  const addWeight = (weightKg) => {
    mutation.mutate({ animalId: id, payload: { weight_kg: weightKg }, idempotencyKey: crypto.randomUUID() });
    if (!onlineManager.isOnline()) {
      toast('Pesée enregistrée — synchronisation en attente', { icon: '📴' });
    }
  };

  return { addWeight, isSaving: mutation.isPending };
}
