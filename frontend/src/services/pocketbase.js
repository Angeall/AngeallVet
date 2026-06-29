import PocketBase from 'pocketbase';

/**
 * Each tenant runs its OWN PocketBase instance (tenant-local auth). The reverse
 * proxy (Caddy) exposes it same-origin under `/pb` on the tenant's sub-domain
 * (e.g. `clinique-martin.angeallvet.fr/pb`). Same-origin keeps the browser
 * talking to PocketBase directly with no CORS and a single certificate.
 *
 * Override with `VITE_POCKETBASE_URL` for local dev (e.g. http://127.0.0.1:8090)
 * or to point at a dedicated PocketBase sub-domain instead.
 */
function resolvePocketBaseUrl() {
  const override = import.meta.env.VITE_POCKETBASE_URL;
  if (override) return override;
  return `${window.location.origin}/pb`;
}

export const POCKETBASE_URL = resolvePocketBaseUrl();

// The SDK persists the auth session in localStorage by default and is safe to
// use as a single global instance on the client.
export const pb = new PocketBase(POCKETBASE_URL);

export const USERS_COLLECTION = import.meta.env.VITE_POCKETBASE_USERS_COLLECTION || 'users';
