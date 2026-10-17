import { test, expect } from '@playwright/test';

test('build, preview, export and persist a bot', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Build your Discord bot.' })).toBeVisible();
  await page.getByRole('link', { name: 'Build a bot', exact: true }).click();
  await expect(page.getByText('Valid flow')).toBeVisible();
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
  const projectId = await page.getByLabel('Projects').inputValue();
  await page.reload();
  await expect(page.getByLabel('Bot name')).toHaveValue('A nicer bot');
  await expect(page.getByLabel('Projects')).toHaveValue(projectId);
  const update = page.waitForResponse(response => response.url().endsWith(`/api/projects/${projectId}`) && response.request().method() === 'PUT');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  expect((await update).status()).toBe(200);
  await page.screenshot({ path: 'test-results/builder-desktop.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('conditions can be added without dragging and preview both branches', async ({ page }) => {
  await page.goto('/builder');
  await page.getByRole('button', { name: 'Condition' }).click();
  await expect(page.getByText('Valid flow')).toBeVisible();
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

test('drag blocks onto the canvas, undo, redo and restore a local draft', async ({ page }) => {
  await page.goto('/builder');
  await expect(page.getByText('Valid flow')).toBeVisible();
  const transfer = await page.evaluateHandle(() => new DataTransfer());
  await page.getByRole('button', { name: 'Embed' }).dispatchEvent('dragstart', { dataTransfer: transfer });
  const bounds = await page.locator('.svelte-flow').boundingBox();
  await page.locator('.svelte-flow').dispatchEvent('drop', { dataTransfer: transfer, clientX: bounds!.x + 100, clientY: bounds!.y + 120 });
  await expect(page.getByLabel('Title', {exact: true})).toHaveValue('New embed');
  await expect(page.getByText('3 blocks', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Undo', exact: true}).click();
  await expect(page.getByText('2 blocks', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Redo', exact: true}).click();
  await expect(page.getByText('3 blocks', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Preview', exact: true}).click();
  await expect(page.locator('.embed-preview')).toContainText('Made for Aaryan.');
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('dbm-draft') || '{}').definition?.nodes.length)).toBe(3);
  await page.reload();
  await expect(page.getByText('3 blocks', {exact: true})).toBeVisible();
});

test('imports a definition and reports invalid graphs without losing editing', async ({ page }) => {
  await page.goto('/builder');
  await expect(page.getByText('Valid flow')).toBeVisible();
  const template = await (await page.request.get('/api/templates')).json();
  await page.locator('input[type=file]').setInputFiles({name: 'bot.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(template.rules))});
  await expect(page.getByText('Definition imported.', {exact: true})).toBeVisible();
  await page.getByLabel('Next step').selectOption('');
  await expect(page.locator('.canvas-status')).toContainText('Connect at least two blocks');
  await page.getByRole('button', {name: 'Undo', exact: true}).click();
  await expect(page.getByText('Valid flow')).toBeVisible();
});

test('theme choice survives navigation and the landing page fits mobile', async ({ page }) => {
  await page.goto('/builder');
  await expect(page.getByText('Valid flow')).toBeVisible();
  await page.getByRole('button', {name: 'Switch to light theme'}).click();
  await expect(page.locator('html')).toHaveClass('light');
  await page.screenshot({path: 'test-results/builder-light.png', fullPage: true});
  await page.getByRole('link', {name: 'Discord Bot Maker.'}).click();
  await expect(page.getByRole('heading', {name: 'Build your Discord bot.'})).toBeVisible();
  await page.reload();
  await expect(page.locator('html')).toHaveClass('light');
  for (const width of [320, 390]) {
    await page.setViewportSize({width, height: 844});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.screenshot({path: 'test-results/landing-mobile.png', fullPage: true});
});

test('minimap drawing fits its panel and shows the entire flow in both themes', async ({ page }) => {
  await page.goto('/builder');
  await expect(page.getByText('Valid flow')).toBeVisible();
  const overview = page.getByRole('img', { name: 'Flow overview' });
  for (const theme of ['dark', 'light']) {
    if (theme === 'light') await page.getByRole('button', {name: 'Switch to light theme'}).click();
    await expect(overview).toBeVisible();
    const geometry = await overview.evaluate(svg => {
      const panel = svg.parentElement!.getBoundingClientRect();
      const drawing = svg.getBoundingClientRect();
      const nodes = [...svg.querySelectorAll('rect')].map(node => node.getBoundingClientRect());
      return {
        fitsPanel: drawing.left >= panel.left && drawing.top >= panel.top && drawing.right <= panel.right && drawing.bottom <= panel.bottom,
        showsNodes: nodes.length === 2 && nodes.every(node => node.left >= drawing.left && node.top >= drawing.top && node.right <= drawing.right && node.bottom <= drawing.bottom)
      };
    });
    expect(geometry).toEqual({ fitsPanel: true, showsNodes: true });
    await page.locator('.canvas-area').screenshot({path: `test-results/minimap-${theme}.png`});
  }
});

test('message previews have server-rendered metadata and a full-size public image', async ({ request, baseURL }) => {
  for (const path of ['/', '/help', '/builder']) {
    const response = await request.get(path);
    expect(response.status()).toBe(200);
    const html = await response.text();
    expect(html).toContain(`property="og:image" content="${baseURL}/social-preview.png"`);
    expect(html).toContain('name="twitter:card" content="summary_large_image"');
    expect(html).toContain('property="og:title" content="Discord Bot Maker"');
  }
  const image = await request.get('/social-preview.png');
  expect(image.status()).toBe(200);
  expect(image.headers()['content-type']).toContain('image/png');
  const png = await image.body();
  expect(png.readUInt32BE(16)).toBe(1200);
  expect(png.readUInt32BE(20)).toBe(630);
});

test('browser defenses and proxy limits are enforced', async ({ page, request, baseURL }) => {
  const response = await request.get('/builder');
  expect(response.headers()['x-frame-options']).toBe('DENY');
  expect(response.headers()['x-content-type-options']).toBe('nosniff');
  expect(response.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  expect(response.headers()['content-security-policy']).toContain("object-src 'none'");
  const oversized = await request.post('/api/validate', { data: 'x'.repeat(262145), headers: {Origin: baseURL!} });
  expect(oversized.status()).toBe(413);
  const crossOrigin = await request.post('/api/validate', {data: {}, headers: {Origin: 'https://untrusted.example'}});
  expect(crossOrigin.status()).toBe(403);
  await page.goto('/builder');
  await expect(page.getByText('Valid flow')).toBeVisible();
  await page.getByRole('button', {name: 'List', exact: true}).click();
  await page.locator('.flow-list button').filter({hasText: 'Send a reply'}).click();
  await page.getByLabel('Reply message').fill('<img src=x onerror="window.untrustedExecuted=true">');
  await page.getByRole('button', {name: 'Preview', exact: true}).click();
  await expect(page.locator('.preview-output')).toContainText('<img src=x');
  expect(await page.evaluate(() => 'untrustedExecuted' in window)).toBe(false);
  await expect(page.locator('.preview-output img')).toHaveCount(0);
});

test('public API requests are rate limited', async ({ request }) => {
  let status = 200;
  for (let attempt = 0; attempt < 121 && status !== 429; attempt++) {
    status = (await request.get('/api/config')).status();
  }
  expect(status).toBe(429);
});
