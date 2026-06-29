// Shared helpers for the hermetic Playwright e2e suite.
//
// Every backend / PocketBase call is intercepted with page.route so the tests
// run without any real backend, database or PocketBase instance.

function b64url(obj) {
  return Buffer.from(JSON.stringify(obj)).toString('base64url');
}

// A structurally-valid (but unsigned) JWT so the PocketBase SDK's authStore
// considers the session valid (it only decodes `exp`, it doesn't verify).
export function makeFakeJWT(payload = {}) {
  const header = { alg: 'HS256', typ: 'JWT' };
  const body = { exp: Math.floor(Date.now() / 1000) + 3600, ...payload };
  return `${b64url(header)}.${b64url(body)}.sig`;
}

export const defaultUser = {
  id: 1,
  pb_user_id: 'pb_admin',
  email: 'admin@angeallvet.fr',
  first_name: 'Sophie',
  last_name: 'Martin',
  role: 'admin',
  phone: null,
  is_active: true,
  sidenav_color: null,
  created_at: '2026-01-01T00:00:00Z',
};

export const adminPermissions = {
  dashboard: true, clients: true, animals: true, agenda: true,
  waiting_room: true, medical: true, inventory: true, invoices: true,
  estimates: true, sales: true, hospitalization: true, communications: true,
  users: true, stats: true,
};

/**
 * Install the full set of network stubs on a page.
 * Routes added later take priority in Playwright, so the catch-all is
 * registered first and the specific overrides after it.
 */
export async function installMocks(page, { user = defaultUser, permissions = adminPermissions, clients = [] } = {}) {
  const pbToken = makeFakeJWT({ id: user.pb_user_id });
  const record = { id: user.pb_user_id, email: user.email };

  // Catch-all: any other API call returns an empty list (dashboard is
  // best-effort and tolerates this).
  await page.route('**/api/v1/**', (route) => route.fulfill({ json: [] }));

  // Backend auth/profile endpoints.
  await page.route('**/auth/session', (route) =>
    route.fulfill({
      json: {
        access_token: makeFakeJWT({ sub: user.pb_user_id }),
        refresh_token: pbToken,
        token_type: 'bearer',
        user,
      },
    })
  );
  await page.route('**/api/v1/auth/me', (route) => route.fulfill({ json: user }));
  await page.route('**/api/v1/auth/permissions/me', (route) =>
    route.fulfill({ json: { role: user.role, permissions } })
  );
  await page.route('**/api/v1/auth/notifications/unread-count', (route) =>
    route.fulfill({ json: { count: 0 } })
  );
  await page.route('**/api/v1/clients**', (route) => route.fulfill({ json: clients }));

  // PocketBase (browser-direct auth).
  await page.route('**/api/collections/*/auth-with-password', (route) =>
    route.fulfill({ json: { token: pbToken, record } })
  );
  await page.route('**/api/collections/*/auth-refresh', (route) =>
    route.fulfill({ json: { token: pbToken, record } })
  );
}

export async function login(page, { email = 'admin@angeallvet.fr', password = 'admin123' } = {}) {
  await page.goto('/login');
  await page.getByPlaceholder('nom@clinique.fr').fill(email);
  await page.getByPlaceholder('Votre mot de passe').fill(password);
  await page.getByRole('button', { name: 'Se connecter' }).click();
}
