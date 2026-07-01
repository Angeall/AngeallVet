// Mobile-friendliness regression: no screen or form should overflow the
// viewport horizontally on a phone-sized window.
import { test, expect } from '@playwright/test';
import { installMocks, login } from './helpers';

test.use({ viewport: { width: 390, height: 844 } }); // iPhone 12-ish

const ROUTES = [
  '/', '/agenda', '/waiting-room', '/clients', '/animals', '/hospitalization',
  '/associations', '/inventory', '/controlled-substances', '/invoices',
  '/estimates', '/sales', '/debts', '/stats', '/communications', '/users',
  '/billing-rules', '/accounting', '/settings',
];

const EMPTY_STATS = {
  total_revenue: 0, total_ht: 0, total_ttc: 0, total_vat: 0,
  total_paid: 0, total_unpaid: 0, invoice_count: 0, paid_count: 0, by_status: {},
};

async function extraMocks(page) {
  const json = (body) => (route) => route.fulfill({ json: body });
  await page.route('**/api/v1/billing/stats**', json({
    period: 'month', start: '2026-07-01', end: '2026-07-31',
    current: EMPTY_STATS, previous: EMPTY_STATS, daily: [], by_payment_method: {},
  }));
  await page.route('**/api/v1/settings/clinic**', json({ id: 1, clinic_name: 'Clinique', country: 'France' }));
  await page.route('**/api/v1/billing/commissions**', json({ veterinarians: [], total: 0 }));
  await page.route('**/api/v1/auth/modules**', json({ modules: [], available: [] }));
  await page.route('**/api/v1/accounting/cash/day**', json({
    date: '2026-07-01', totals_by_method: { cash: 120, card: 80 }, method_labels: {},
    total: 200, payment_count: 5, cash_payments: 120, cash_in: 0, cash_out: 0,
    cash_movement_net: 120, movements: [], closed: false, closing: null,
  }));
  await page.route('**/api/v1/accounting/cash/closings**', json([]));
}

async function hOverflow(page) {
  return page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
}

test('no screen overflows the phone viewport horizontally', async ({ page }) => {
  await installMocks(page);
  await extraMocks(page);
  await login(page);
  await expect(page).toHaveURL(/\/$/);

  const offenders = [];
  for (const route of ROUTES) {
    await page.goto(route);
    await page.waitForTimeout(450);
    const { scrollWidth, clientWidth } = await hOverflow(page);
    if (scrollWidth > clientWidth + 2) offenders.push(`${route}  (${scrollWidth} > ${clientWidth})`);
  }
  expect(offenders, `Horizontal overflow on:\n${offenders.join('\n')}`).toEqual([]);
});

test('the off-canvas sidebar opens from the menu toggle', async ({ page }) => {
  await installMocks(page);
  await extraMocks(page);
  await login(page);
  // Sidebar starts off-canvas; the burger is visible on mobile.
  const toggle = page.locator('.menu-toggle');
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect(page.locator('.sidebar.open')).toBeVisible();
});

test('open forms fit the phone viewport', async ({ page }) => {
  await installMocks(page);
  await extraMocks(page);
  await login(page);

  // Billing-rules: the rule editor (component + tier variants).
  await page.goto('/billing-rules');
  await page.getByRole('button', { name: '+ Nouvelle règle' }).click();
  let m = await hOverflow(page);
  expect(m.scrollWidth, 'rule form (components) overflows').toBeLessThanOrEqual(m.clientWidth + 2);
  await page.locator('select').filter({ hasText: 'Composants (par ligne)' }).first().selectOption('tier');
  await page.waitForTimeout(200);
  m = await hOverflow(page);
  expect(m.scrollWidth, 'rule form (tier) overflows').toBeLessThanOrEqual(m.clientWidth + 2);

  // Settings is the most form-dense page.
  await page.goto('/settings');
  await page.waitForTimeout(300);
  m = await hOverflow(page);
  expect(m.scrollWidth, 'settings overflows').toBeLessThanOrEqual(m.clientWidth + 2);
});
