import { test, expect } from '@playwright/test';

test('build, preview, export and persist a bot', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Your server.Your ideas.Your bot.' })).toBeVisible();
  await page.getByRole('link', { name: 'Build a bot', exact: true }).click();
  await expect(page.getByText('All connected. Looking good.')).toBeVisible();
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await page.locator('.flow-list button').filter({ hasText: 'Send a reply' }).click();
  await page.getByLabel('Reply message').fill('Made for {{user.display_name}}.');
  await page.getByRole('button', { name: 'Preview', exact: true }).click();
  await expect(page.locator('.preview-output')).toContainText('Made for Aaryan.');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('discord-bot.zip');
  await page.getByRole('button', { name: 'Local sign in' }).click();
  await expect(page.getByText('Local developer')).toBeVisible();
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Project saved.', { exact: true })).toBeVisible();
  await page.getByLabel('Bot name').fill('A nicer bot');
  await page.getByLabel('Bot name').blur();
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Project saved.', { exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('dbm-draft'))).toContain('A nicer bot');
  await page.reload();
  await expect(page.getByLabel('Bot name')).toHaveValue('A nicer bot');
  expect(errors).toEqual([]);
});

test('conditions can be added without dragging and preview both branches', async ({ page }) => {
  await page.goto('/builder');
  await page.getByRole('button', { name: 'Condition Give it a little logic' }).click();
  await expect(page.getByText('All connected. Looking good.')).toBeVisible();
  await page.getByRole('button', { name: 'Preview', exact: true }).click();
  await expect(page.locator('.preview-output')).toContainText('This command is not available here.');
  await page.getByRole('button', { name: 'Edit sample context' }).click();
  await page.getByLabel('Role IDs (comma separated)').fill('123456789');
  await page.getByRole('button', { name: 'Preview', exact: true }).click();
  await expect(page.locator('.preview-output')).toContainText('Hello, Aaryan!');
});

test('mobile layout has no horizontal overflow and supports list editing', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/builder');
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await page.locator('.flow-list button').filter({ hasText: 'Send a reply' }).click();
  await expect(page.getByLabel('Reply message')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/builder-mobile.png', fullPage: true });
});
