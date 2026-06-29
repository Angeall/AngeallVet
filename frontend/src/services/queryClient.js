import { QueryClient } from '@tanstack/react-query';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { get, set, del } from 'idb-keyval';

// Version du schéma de cache. À incrémenter pour invalider les caches déjà
// persistés si la forme des données change de façon incompatible.
export const CACHE_VERSION = 'v1';

// Le cache hors ligne est cloisonné par tenant. Chaque tenant ayant son propre
// sous-domaine, le hostname suffit à isoler les données : aucune fuite entre
// cliniques qui partageraient un même navigateur.
const TENANT_NS = typeof window !== 'undefined' ? window.location.hostname : 'default';
export const CACHE_STORAGE_KEY = `angeallvet-cache-${TENANT_NS}-${CACHE_VERSION}`;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // On conserve les données longtemps pour pouvoir les resservir hors
      // ligne ; elles sont revalidées en arrière-plan dès le retour du réseau.
      staleTime: 30 * 1000,
      gcTime: 7 * 24 * 60 * 60 * 1000, // 7 jours
      retry: 2,
      refetchOnWindowFocus: false,
    },
    mutations: {
      // En mode réseau « online » (défaut), une mutation lancée hors ligne est
      // mise en pause puis rejouée à la reconnexion (resumePausedMutations).
      retry: 0,
    },
  },
});

// Persistance asynchrone vers IndexedDB — bien plus adapté que localStorage
// (limité à ~5 Mo et synchrone) pour des dossiers médicaux.
export const persister = createAsyncStoragePersister({
  key: CACHE_STORAGE_KEY,
  throttleTime: 1000,
  storage: {
    getItem: (key) => get(key),
    setItem: (key, value) => set(key, value),
    removeItem: (key) => del(key),
  },
});

// Purge complète : à appeler à la déconnexion / au changement de tenant pour ne
// laisser aucune donnée patient au repos sur le poste.
export async function clearOfflineCache() {
  queryClient.getMutationCache().clear();
  queryClient.clear();
  try {
    await persister.removeClient();
  } catch {
    // best-effort : la purge mémoire a déjà eu lieu.
  }
}
