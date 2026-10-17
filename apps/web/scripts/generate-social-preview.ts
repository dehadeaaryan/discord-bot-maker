import { chromium } from '@playwright/test';
import { resolve } from 'node:path';

// Capture the real landing page, using its fonts, logo and components.
// Run the web dev server first; PREVIEW_BASE_URL can select another local port.
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  await page.goto(process.env.PREVIEW_BASE_URL || 'http://localhost:5173', { waitUntil: 'networkidle' });
  await page.evaluate(async () => {
    localStorage.removeItem('dbm-theme');
    document.documentElement.classList.remove('light');
    await document.fonts.ready;
  });
  await page.addStyleTag({ content: `
    .site-nav, .landing footer { display: none !important; }
    .site-header { width: calc(100% - 80px); margin-top: 32px; box-shadow: none; }
    .landing { padding: 0 40px; }
    .hero { min-height: 0; padding: 66px 0 0; gap: 48px; }
    .hero h1 { font-size: 68px; }
    .hero-description { font-size: 17px; }
    .hero-workspace { box-shadow: none; }
    .demo-node strong { font-size: 13px; }
    *, *::before, *::after { animation: none !important; transition: none !important; }
  ` });
  await page.locator('.brand-link img').evaluate(async image => { await (image as HTMLImageElement).decode(); });
  await page.screenshot({ path: resolve('static/social-preview.png') });
  console.log('Created static/social-preview.png (1200 × 630).');
} finally {
  await browser.close();
}
