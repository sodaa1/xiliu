const { chromium, browserChannel, previewUrl } = require("./runtime.cjs");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({
    channel: browserChannel,
    headless: true,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 900 },
    });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 400)
        errors.push(`${response.status()} ${response.url()}`);
    });
    await page.goto(previewUrl, { waitUntil: "networkidle" });
    assert.equal(
      await page.locator("html").getAttribute("data-showcase"),
      "public",
    );
    const githubLinks = await page
      .locator('a[href*="github.com"]')
      .evaluateAll((links) => links.map((link) => link.href));
    assert(githubLinks.length >= 2);
    assert(
      githubLinks.every((url) =>
        url.startsWith("https://github.com/sodaa1/xiliu"),
      ),
    );
    assert.equal(await page.locator('a[href="/today"]').count(), 0);
    assert.match(
      await page.locator("body").innerText(),
      /个人信息与 AI 助手 · 0.3.0/,
    );
    assert.match(
      await page.locator("#install pre").innerText(),
      /git clone https:\/\/github.com\/sodaa1\/xiliu.git\ncd xiliu/,
    );
    assert.match(await page.locator("#install").innerText(), /Python 3.12\+/);
    await page.locator("#install").scrollIntoViewIfNeeded();
    await page.waitForTimeout(700);
    await page.screenshot({ path: ".preview/intro-install-current.png" });
    if (process.env.APP_INTRO_URL) {
      await page.goto(process.env.APP_INTRO_URL, { waitUntil: "networkidle" });
      assert.equal(
        await page.locator("html").getAttribute("data-showcase"),
        null,
      );
      assert((await page.locator('a[href="/today"]').count()) > 0);
      assert.match(await page.locator("h1").innerText(), /信息有归处/);
      await page.screenshot({ path: ".preview/intro-app-current.png" });
    }
    assert.deepEqual(errors, []);
    console.log(
      "Current repository, version, installation, public/local navigation and browser assets: passed",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
