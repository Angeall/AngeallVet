import { test, expect } from '@playwright/test';
import { installMocks, login } from './helpers';

// Exercises the reusable offline-mutation path (useOfflineMutation) shared by
// the clients list, the agenda and the animal-page writes: optimistic insert,
// offline badge, idempotent replay on reconnect.
test('creates a client offline: optimistic row, badge, then syncs on reconnect', async ({ page }) => {
  const idemKeys = [];
  let clients = [];
  await installMocks(page);
  await page.route('**/api/v1/clients**', async (route) => {
    const req = route.request();
    if (req.method() === 'POST') {
      const key = req.headers()['idempotency-key'];
      if (key) idemKeys.push(key);
      const body = JSON.parse(req.postData() || '{}');
      const c = { id: 50, animal_count: 0, account_balance: 0, ...body };
      clients = [c, ...clients];
      await route.fulfill({ status: 201, json: c });
    } else {
      await route.fulfill({ json: clients });
    }
  });

  await login(page);
  await page.getByRole('link', { name: 'Clients', exact: true }).click();
  await expect(page).toHaveURL(/\/clients$/);
  // Wait for the lazy-loaded ClientsPage chunk to fetch + render while online,
  // before simulating offline (a not-yet-loaded route chunk can't be fetched
  // once offline — that needs the service worker precache, see offline roadmap).
  await expect(page.getByRole('button', { name: /Nouveau client/ })).toBeVisible();

  await page.context().setOffline(true);

  await page.getByRole('button', { name: /Nouveau client/ }).click();
  const formCard = page.locator('.card').filter({ hasText: 'Nouveau client' });
  await formCard.locator('input.form-input').nth(0).fill('Camille');
  await formCard.locator('input.form-input').nth(1).fill('Offline');
  await formCard.getByRole('button', { name: 'Enregistrer' }).click();

  // The client appears immediately and the restricted-mode badge shows.
  await expect(page.getByText('Offline Camille')).toBeVisible();
  await expect(page.getByRole('button', { name: /Hors ligne/ })).toBeVisible();
  expect(idemKeys.length).toBe(0);

  // Reconnect: the queued create replays with its idempotency key, badge clears.
  await page.context().setOffline(false);
  await expect(page.getByRole('button', { name: /Hors ligne/ })).toHaveCount(0);
  await expect.poll(() => idemKeys.length).toBeGreaterThan(0);
});
