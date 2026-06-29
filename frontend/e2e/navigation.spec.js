import { test, expect } from '@playwright/test';
import { installMocks, login, defaultUser } from './helpers';

test('navigates to the clients page and renders the stubbed list', async ({ page }) => {
  await installMocks(page, {
    clients: [
      { id: 1, first_name: 'Jean', last_name: 'Moreau', phone: '0102030405', email: 'jean@x.fr', is_active: true },
      { id: 2, first_name: 'Marie', last_name: 'Lefevre', mobile: '0612345678', is_active: true },
    ],
  });
  await login(page);

  await page.getByRole('link', { name: 'Clients', exact: true }).click();
  await expect(page).toHaveURL(/\/clients$/);
  await expect(page.getByRole('heading', { name: 'Clients' })).toBeVisible();
  await expect(page.getByText('2 client(s) enregistre(s)')).toBeVisible();
});

test('RBAC: an accountant does not see clinical menu entries', async ({ page }) => {
  await installMocks(page, {
    user: { ...defaultUser, role: 'accountant' },
    permissions: {
      dashboard: true, clients: true, animals: false, agenda: false,
      waiting_room: false, medical: false, inventory: true, invoices: true,
      estimates: true, sales: true, hospitalization: false,
      communications: false, users: false, stats: true,
    },
  });
  await login(page);

  // Allowed entries are present (exact match to avoid dashboard stat-card links)…
  await expect(page.getByRole('link', { name: 'Factures', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Statistiques', exact: true })).toBeVisible();
  // …clinical ones are filtered out.
  await expect(page.getByRole('link', { name: 'Animaux', exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Agenda', exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: "Salle d'attente", exact: true })).toHaveCount(0);
});
