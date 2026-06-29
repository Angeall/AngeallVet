import { test, expect } from '@playwright/test';
import { installMocks, login } from './helpers';

const animal = {
  id: 1, client_id: 1, name: 'Rex', species: 'dog', breed: 'Labrador',
  sex: 'male', vital_status: 'alive', is_neutered: false, alerts: [],
  microchip_number: null, tattoo_number: null, date_of_birth: null, color: null, notes: null,
};

// Stateful stub for the animal-detail data: POSTed records persist so the
// post-success refetch keeps them, and every POST's Idempotency-Key is captured.
async function mockAnimalDetail(page) {
  let records = [];
  let nextId = 100;
  const idemKeys = [];
  await page.route('**/api/v1/animals/1', (route) => route.fulfill({ json: animal }));
  await page.route('**/api/v1/medical/records**', async (route) => {
    const req = route.request();
    if (req.method() === 'POST') {
      const key = req.headers()['idempotency-key'];
      if (key) idemKeys.push(key);
      const body = JSON.parse(req.postData() || '{}');
      const rec = { id: nextId++, animal_id: 1, created_at: new Date().toISOString(), home_treatment_products: [], ...body };
      records = [rec, ...records];
      await route.fulfill({ status: 201, json: rec });
    } else {
      await route.fulfill({ json: records });
    }
  });
  return { idemKeys };
}

async function openLoggedInAnimalPage(page) {
  await login(page);
  // Wait for the authenticated shell before navigating.
  await expect(page.getByPlaceholder('Rechercher un client, animal, produit...')).toBeVisible();
  await page.goto('/animals/1');
  await expect(page.getByRole('heading', { name: 'Rex' })).toBeVisible();
}

test('creates a consultation online and it survives the refetch', async ({ page }) => {
  await installMocks(page);
  const { idemKeys } = await mockAnimalDetail(page);
  await openLoggedInAnimalPage(page);

  await page.getByRole('button', { name: '+ Nouveau dossier' }).click();
  await page.getByPlaceholder('Symptomes rapportes par le proprietaire...').fill('Online test motif');
  await page.getByRole('button', { name: 'Enregistrer le dossier' }).click();

  // Visible immediately (optimistic) and still there after the success refetch.
  await expect(page.getByText('Online test motif')).toBeVisible();
  // The write carried an Idempotency-Key header.
  expect(idemKeys.length).toBeGreaterThan(0);
});

test('creates a consultation offline: optimistic, badge shows, then syncs on reconnect', async ({ page }) => {
  await installMocks(page);
  const { idemKeys } = await mockAnimalDetail(page);
  await openLoggedInAnimalPage(page);

  await page.context().setOffline(true);

  await page.getByRole('button', { name: '+ Nouveau dossier' }).click();
  await page.getByPlaceholder('Symptomes rapportes par le proprietaire...').fill('Offline test motif');
  await page.getByRole('button', { name: 'Enregistrer le dossier' }).click();

  // The consultation appears even offline, and the restricted-mode badge shows.
  await expect(page.getByText('Offline test motif')).toBeVisible();
  await expect(page.getByRole('button', { name: /Hors ligne/ })).toBeVisible();
  // Nothing was sent to the server while offline.
  expect(idemKeys.length).toBe(0);

  // Reconnect: the queued write replays (no data lost) and the badge clears.
  await page.context().setOffline(false);
  await expect(page.getByText('Offline test motif')).toBeVisible();
  await expect(page.getByRole('button', { name: /Hors ligne/ })).toHaveCount(0);
  await expect.poll(() => idemKeys.length).toBeGreaterThan(0);
});
