const fs = require("node:fs");
const path = require("node:path");

const siteRoot = path.resolve(__dirname, "../..");
const output = path.join(siteRoot, ".preview");
fs.mkdirSync(output, { recursive: true });
process.chdir(siteRoot);

function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE)
    return require(process.env.PLAYWRIGHT_MODULE);
  try {
    return require("playwright");
  } catch {
    throw new Error(
      "Set PLAYWRIGHT_MODULE to an installed Playwright module, or install Playwright locally for browser QA.",
    );
  }
}

module.exports = {
  ...loadPlaywright(),
  browserChannel: process.env.BROWSER_CHANNEL || "msedge",
  previewUrl: process.env.INTRO_URL || "http://127.0.0.1:5183/",
};
