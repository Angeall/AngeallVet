import { test, expect } from '@playwright/test';
import { installMocks, login, defaultUser } from './helpers';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page);
  });

  test('logs in and lands on the app shell', async ({ page }) => {
    await login(page);
    // The sidebar (only rendered when authenticated) is visible.
    await expect(page.getByRole('link', { name: 'Tableau de bord' })).toBeVisible();
    await expect(
      page.getByText(`${defaultUser.first_name} ${defaultUser.last_name}`)
    ).toBeVisible();
  });

  test('shows an error and stays on /login with bad credentials', async ({ page }) => {
    // Override the PocketBase login to fail (added after installMocks -> wins).
    await page.route('**/api/collections/*/auth-with-password', (route) =>
      route.fulfill({ status: 400, json: { message: 'Failed to authenticate.' } })
    );

    await page.goto('/login');
    await page.getByPlaceholder('nom@clinique.fr').fill('admin@angeallvet.fr');
    await page.getByPlaceholder('Votre mot de passe').fill('wrong-password');
    await page.getByRole('button', { name: 'Se connecter' }).click();

    await expect(page.getByText('Email ou mot de passe incorrect')).toBeVisible();
    await expect(page.getByPlaceholder('nom@clinique.fr')).toBeVisible();
  });

  test('redirects unauthenticated visitors to /login', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible();
  });

  test('logs out back to /login', async ({ page }) => {
    await login(page);
    await expect(page.getByRole('link', { name: 'Tableau de bord' })).toBeVisible();

    await page.getByTitle('Se deconnecter').click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test('keeps the session across a reload', async ({ page }) => {
    await login(page);
    await expect(page.getByRole('link', { name: 'Tableau de bord' })).toBeVisible();

    await page.reload();
    // PocketBase session is restored from localStorage and re-exchanged.
    await expect(page.getByRole('link', { name: 'Tableau de bord' })).toBeVisible();
  });
});
