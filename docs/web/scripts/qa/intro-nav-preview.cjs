const { chromium, browserChannel, previewUrl } = require("./runtime.cjs");
const fs = require("node:fs");
const assert = require("node:assert/strict");
(async () => {
  const before = process.argv.includes("--before");
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1536, height: 1024 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(previewUrl, { waitUntil: "networkidle" });
  const prefix = `.preview/intro-nav-${before ? "before" : "after"}`;
  await page.screenshot({ path: `${prefix}-hero.png` });
  await page
    .locator(".intro-header")
    .screenshot({ path: `${prefix}-header.png` });
  if (before) {
    await browser.close();
    return;
  }
  const nav = page.getByRole("navigation", { name: "介绍页导航" });
  const feature = nav.getByRole("link", { name: "功能", exact: true });
  assert.equal(await nav.locator('svg[aria-hidden="true"]').count(), 4);
  await feature.hover();
  await page.waitForTimeout(300);
  await page
    .locator(".intro-header")
    .screenshot({ path: `${prefix}-hover.png` });
  await page.screenshot({
    path: `${prefix}-detail.png`,
    clip: { x: 800, y: 8, width: 580, height: 64 },
  });
  await page.mouse.move(20, 100);
  await page.evaluate(() => window.scrollTo(0, 750));
  await page.waitForTimeout(1300);
  await page.screenshot({ path: `${prefix}-workspace.png` });
  await feature.evaluate((el) => el.focus({ preventScroll: true }));
  assert(await feature.evaluate((el) => el === document.activeElement));
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => {
    const y = document.querySelector("#features").getBoundingClientRect().top;
    return y >= 80 && y < 300;
  });
  assert.equal(new URL(page.url()).hash, "#features");
  const destination = await page.locator("#features").boundingBox();
  assert(destination && destination.y >= 80 && destination.y < 300);
  const sizes = [1536, 1024, 901, 820, 701, 390];
  for (const width of sizes) {
    await page.setViewportSize({ width, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(250);
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `overflow at ${width}`,
    );
    if (width <= 900) {
      const menu = page.getByRole("button", { name: "打开导航" });
      await menu.click();
      const target = nav.getByRole("link", { name: "工作流", exact: true });
      assert(await target.isVisible());
      const bounds = await target.boundingBox();
      assert(bounds.height >= 44);
      if (width === 390)
        await page.screenshot({ path: `${prefix}-mobile-menu.png` });
      await target.click();
      assert.equal(new URL(page.url()).hash, "#workflow");
      assert.equal(await menu.getAttribute("aria-expanded"), "false");
    }
  }
  assert.equal(errors.length, 0);
  fs.writeFileSync(
    ".preview/intro-nav-report.json",
    JSON.stringify(
      {
        iconLinks: 4,
        keyboardAnchorAndFocus: true,
        responsiveWidths: sizes,
        mobileTouchTarget: "44px minimum",
        errors,
      },
      null,
      2,
    ),
  );
  console.log(
    "Navigation icons, hover capture, keyboard anchors, six widths and mobile navigation: passed",
  );
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
