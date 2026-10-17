const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || path.join(require('node:os').homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const origin = 'http://127.0.0.1:8767';
const password = 'Disposable-browser-password-17';
const checks = [];
const check = (name, value) => { assert(value, name); checks.push(name); };
async function session(context) { return (await context.request.get(origin + '/api/auth/session')).json(); }
async function headers(context) { const s = await session(context); return { Origin: origin, 'X-CSRF-Token': s.csrf_token, 'X-Workspace-ID': s.workspace.id }; }
async function api(context, url, data, method = 'POST') {
  return context.request.fetch(origin + url, { method, data, headers: await headers(context) });
}
async function register(page, name) {
  await page.goto(origin + '/today');
  await page.getByRole('button', { name: /创建一个/ }).click();
  await page.getByLabel('账号', { exact: true }).fill(name);
  await page.getByLabel('密码', { exact: true }).fill(password);
  await page.getByRole('button', { name: '注册并开始使用' }).click();
  await page.locator('.cloud-account').getByText(name).waitFor();
  await page.getByRole('button', { name: '关闭引导' }).click();
}
async function assistant(page) {
  await page.goto(origin + '/assistant');
  await page.getByLabel('消息', { exact: true }).waitFor();
}
async function send(page, text, remaining) {
  await page.getByLabel('消息', { exact: true }).fill(text);
  await page.getByRole('button', { name: '发送消息', exact: true }).click();
  await page.waitForFunction(n => document.body.innerText.includes(`剩余 ${n}/5 次`), remaining);
  await page.getByRole('button', { name: '停止回复', exact: true }).waitFor({ state: 'hidden' });
}
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const errors = [];
  try {
    const a = await browser.newContext({ viewport: { width: 1440, height: 960 } });
    const b = await browser.newContext({ viewport: { width: 1440, height: 960 } });
    const page = await a.newPage(), other = await b.newPage();
    page.on('pageerror', error => errors.push(error.message));
    other.on('pageerror', error => errors.push(error.message));
    const suffix = Date.now();
    const alice = 'alice' + suffix, bob = 'bobby' + suffix;
    await register(page, alice); await register(other, bob);
    check('two independent authenticated contexts', (await session(a)).workspace.id !== (await session(b)).workspace.id);
    const note = await (await api(a, '/api/content', { type: 'note', status: 'inbox', title: '甲账户专属资料', content: 'Alice private' })).json();
    await api(b, '/api/content', { type: 'note', status: 'inbox', title: '乙账户专属资料', content: 'Bob private' });
    await page.goto(origin + '/inbox'); await page.getByText('甲账户专属资料', { exact: true }).waitFor();
    await other.goto(origin + '/inbox'); await other.getByText('乙账户专属资料', { exact: true }).waitFor();
    check('UI account data isolation', !(await other.getByText('甲账户专属资料', { exact: true }).count()));
    const file = await (await api(a, '/api/content', { type: 'file', status: 'inbox', title: '附件', filename: 'sample.txt', data_base64: Buffer.from('private file').toString('base64') })).json();
    check('authenticated attachment download', (await (await a.request.get(origin + `/api/content/${file.id}/original`)).body()).toString() === 'private file');
    check('cross-account attachment rejection', (await b.request.get(origin + `/api/content/${file.id}/original`)).status() === 404);
    await assistant(page);
    const sent = [];
    page.on('request', request => { if (/\/chat$/.test(request.url())) sent.push({ url: request.url(), body: request.postDataJSON() }); });
    await send(page, 'first trial', 4);
    const before = (await (await a.request.get(sent[0].url.replace(/\/chat$/, '/messages'))).json()).length;
    await a.request.post(sent[0].url, { data: sent[0].body, headers: await headers(a) });
    check('duplicate request replays without new messages or quota', (await session(a)).trial.remaining === 4 && (await (await a.request.get(sent[0].url.replace(/\/chat$/, '/messages'))).json()).length === before);
    await page.getByLabel('消息', { exact: true }).fill('slow-response stop');
    await page.getByRole('button', { name: '发送消息', exact: true }).click();
    await page.locator('.active-thinking .run-status').filter({ hasText: '正在生成回答…' }).waitFor();
    await page.getByRole('button', { name: '停止回复', exact: true }).click();
    await page.waitForFunction(() => document.body.innerText.includes('剩余 3/5 次'));
    await page.getByText('已停止本次回复。', { exact: true }).first().waitFor();
    check('started stop consumes one trial', (await session(a)).trial.remaining === 3);
    const detached = await a.newPage();
    await assistant(detached);
    await detached.getByLabel('消息', { exact: true }).fill('slow-response disconnect');
    await detached.getByRole('button', { name: '发送消息', exact: true }).click();
    await detached.locator('.active-thinking .run-status').filter({ hasText: '正在生成回答…' }).waitFor();
    await detached.close();
    await page.waitForTimeout(700);
    check('browser disconnect does not refund started generation', (await session(a)).trial.remaining === 2);
    await assistant(page);
    await send(page, 'connection-fail', 2);
    check('unstarted connection failure refunds', (await session(a)).trial.remaining === 2);
    await send(page, 'fourth counted trial', 1);
    await send(page, 'fifth counted trial', 0);
    check('exhausted trial selection disabled', await page.getByRole('radio', { name: /公共试用/ }).isDisabled());
    check('other account quota independent', (await session(b)).trial.remaining === 5);
    await api(a, '/api/settings/model', { provider: 'custom', model: 'fixture-own', base_url: 'https://model.example/v1', api_key: 'disposable-user-key' }, 'PUT');
    await assistant(page);
    await send(page, 'own model', 0);
    check('own API does not consume trial', (await session(a)).trial.remaining === 0);
    check('no API credential in browser storage', !(await page.evaluate(() => JSON.stringify({ ...localStorage }))).includes('disposable-user-key'));
    await page.setViewportSize({ width: 390, height: 844 });
    check('mobile has no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: '.preview/cloud-acceptance-mobile.png' });
    await page.getByRole('button', { name: '退出', exact: true }).click();
    await page.getByLabel('账号', { exact: true }).fill(bob);
    await page.getByLabel('密码', { exact: true }).fill(password);
    await page.getByRole('button', { name: '登录', exact: true }).click();
    await page.locator('.cloud-account').getByText(bob).waitFor();
    await page.goto(origin + '/inbox'); await page.getByText('乙账户专属资料', { exact: true }).waitFor();
    check('same-context switch clears prior workspace cache', !(await page.getByText('甲账户专属资料', { exact: true }).count()));
    check('prior account document still inaccessible after switching', (await a.request.get(origin + '/api/content/' + note.id)).status() === 404);
    const guest = await browser.newPage();
    const requests = [];
    guest.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) requests.push(request.url()); });
    await guest.goto(origin + '/demo/#/today');
    await guest.getByRole('button', { name: '关闭引导' }).waitFor();
    check('guest uses zero real APIs', requests.length === 0);
    check('no browser runtime exceptions', errors.length === 0);
    fs.writeFileSync('.preview/cloud-browser-acceptance.json', JSON.stringify({ passed: true, checks, errors }, null, 2));
    console.log(JSON.stringify({ passed: checks.length, errors }));
  } finally { await browser.close(); }
})().catch(error => { fs.writeFileSync('.preview/cloud-browser-acceptance.json', JSON.stringify({ passed: false, checks, error: error.message }, null, 2)); console.error(error); process.exitCode = 1; });
