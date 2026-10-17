const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || path.join(require('node:os').homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const base = process.env.DEMO_URL || 'http://127.0.0.1:5185/xiliu/';
const output = process.env.DEMO_REPORT || '.preview/pages-browser.json';
const report = { url: base, checks: [], errors: [], failedResponses: [], apiRequests: [] };
function check(name, value) {
  report.checks.push({ name, passed: Boolean(value) });
  if (!value) throw new Error(name);
}
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    page.setDefaultTimeout(12000);
    page.on('pageerror', error => report.errors.push(error.message));
    page.on('response', response => { if (response.status() >= 400) report.failedResponses.push({ url: response.url(), status: response.status() }); });
    page.on('request', request => { if (new URL(request.url()).pathname.includes('/api/')) report.apiRequests.push(request.url()); });
    const initial = await page.goto(base + '#/plans');
    check('Pages entry returns 200 without a server rewrite', initial.status() === 200);
    await page.getByRole('dialog', { name: '欢迎使用息流', exact: true }).waitFor();
    check('first visit opens the guide', true);
    await page.getByRole('button', { name: '下一步', exact: true }).click();
    await page.waitForURL('**/#/today');
    await page.locator('.home-character img').first().waitFor({ state: 'attached' }).catch(() => {});
    await page.waitForFunction(() => [...document.querySelectorAll('img')].every(img => img.complete && img.naturalWidth > 0));
    check('today bundled images load under the repository path', await page.locator('img').count() > 0);
    await page.getByRole('button', { name: '下一步', exact: true }).click();
    await page.waitForURL('**/#/feed');
    check('guide follows hash navigation', await page.getByRole('dialog', { name: '资讯', exact: true }).isVisible());
    await page.getByRole('button', { name: '跳过引导', exact: true }).click();
    await page.waitForURL('**/#/plans');
    for (const route of ['today', 'assistant', 'feed', 'inbox', 'knowledge', 'plans', 'settings']) {
      await page.goto('about:blank');
      const response = await page.goto(base + '#/' + route);
      check(route + ' copied route loads', response.status() === 200);
      await page.locator('#root').waitFor();
      check(route + ' refresh returns 200', (await page.reload()).status() === 200);
      await page.waitForTimeout(120);
    }
    await page.goto(base + '#/today');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('[data-onboarding="help-entry"]').click();
    const panel = page.getByRole('dialog', { name: '欢迎使用息流', exact: true });
    const bounds = await panel.boundingBox();
    check('replayed mobile guide fits the viewport', bounds.x >= 0 && bounds.x + bounds.width <= 390 && bounds.y >= 0 && bounds.y + bounds.height <= 844);
    await page.screenshot({ path: '.preview/pages-mobile.png' });
    await page.getByRole('button', { name: '跳过引导', exact: true }).click();
    check('no real API network requests', report.apiRequests.length === 0);
    check('no missing static assets', report.failedResponses.length === 0);
    check('no page errors', report.errors.length === 0);
    report.status = 'passed';
  } catch (error) { report.status = 'failed'; report.failure = String(error); process.exitCode = 1; }
  finally { fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n'); console.log(JSON.stringify(report, null, 2)); await browser.close(); }
})();
