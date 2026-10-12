const { chromium, browserChannel } = require("./runtime.cjs");
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1536, height: 1024 },
    reducedMotion: "reduce",
  });
  const errors = [],
    failed = [],
    api = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400)
      failed.push({ url: response.url(), status: response.status() });
  });
  page.on("request", (request) => {
    if (request.url().includes("/api/")) api.push(request.url());
  });
  await page.goto(process.env.PORTFOLIO_URL || "http://127.0.0.1:5182/", {
    waitUntil: "networkidle",
  });
  assert.deepEqual(
    (await page.locator(".project-card h3").allTextContents()).slice(0, 2),
    ["息流 · xiliu", "Xiliu Mini"],
  );
  await page.locator("#work").scrollIntoViewIfNeeded();
  await page.screenshot({ path: ".preview/portfolio-xiliu-first.png" });
  await page.getByRole("link", { name: "查看息流", exact: true }).click();
  await page.waitForLoadState("networkidle");
  assert(new URL(page.url()).pathname === "/projects/xiliu/");
  await page.getByRole("heading", { level: 1 }).waitFor();
  assert.equal(
    await page.locator("html").getAttribute("data-showcase"),
    "public",
  );
  assert.equal(
    await page
      .locator('a[href="/today"], a[href="/feed"], a[href="/knowledge"]')
      .count(),
    0,
  );
  assert.equal(
    await page
      .getByRole("link", { name: "GitHub · xiliu" })
      .getAttribute("href"),
    "https://github.com/sodaa1/xiliu",
  );
  assert.equal(
    await page.getByRole("link", { name: "返回作品集" }).getAttribute("href"),
    "https://933693.xyz/",
  );
  await page.locator(".intro-footer").scrollIntoViewIfNeeded();
  await page.screenshot({ path: ".preview/xiliu-public-footer.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.goto(
    new URL(
      "/projects/xiliumini/",
      process.env.PORTFOLIO_URL || "http://127.0.0.1:5182/",
    ).href,
    { waitUntil: "networkidle" },
  );
  await page
    .getByRole("heading", { level: 1, name: "xiliumini", exact: true })
    .waitFor();
  assert.equal(errors.length, 0);
  assert.equal(failed.length, 0);
  assert.equal(api.length, 0);
  const report = {
    projectOrder: ["息流 · xiliu", "Xiliu Mini"],
    nestedAssets: true,
    publicLinks: true,
    githubFooter: true,
    xiliuminiPreserved: true,
    mobileOverflow: false,
    errors,
    failed,
    api,
  };
  fs.writeFileSync(
    ".preview/portfolio-integration-report.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
