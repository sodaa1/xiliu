import { readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import {
  appRequire,
  appRoot,
  dependencyAliases,
  loadBuildTools,
  siteRoot,
} from "./config.mjs";

const mode = process.argv[2] ?? "build";
const localApp = process.argv.includes("--app");
if (mode === "test") {
  const vitestEntry = path.join(
    path.dirname(appRequire.resolve("vitest/package.json")),
    "vitest.mjs",
  );
  const result = spawnSync(
    process.execPath,
    [vitestEntry, "--run", "../docs/web/src/LandingPage.test.tsx"],
    { cwd: appRoot, stdio: "inherit" },
  );
  process.exit(result.status ?? 1);
}
const { vite, react } = await loadBuildTools();
const config = {
  configFile: false,
  root: siteRoot,
  base: "./",
  plugins: [
    react(),
    {
      name: "xiliu-showcase-audience",
      transformIndexHtml: {
        order: "pre",
        handler: (html) =>
          localApp ? html.replace(' data-showcase="public"', "") : html,
      },
    },
  ],
  resolve: { alias: dependencyAliases, dedupe: ["react", "react-dom"] },
};
if (mode === "dev") {
  const server = await vite.createServer({
    ...config,
    server: { host: "127.0.0.1", port: 5183, strictPort: true },
  });
  await server.listen();
  server.printUrls();
} else if (mode === "build") {
  const check = spawnSync(
    process.execPath,
    [
      appRequire.resolve("typescript/lib/tsc.js"),
      "--project",
      path.join(siteRoot, "tsconfig.json"),
    ],
    { stdio: "inherit" },
  );
  if (check.status !== 0) process.exit(check.status ?? 1);
  const output = localApp
    ? path.join(appRoot, "dist", "intro")
    : path.join(siteRoot, "dist");
  await vite.build({ ...config, build: { outDir: output, emptyOutDir: true } });
  if (localApp) {
    const file = path.join(output, "index.html");
    writeFileSync(
      file,
      readFileSync(file, "utf8").replace(/\s*<link rel="canonical"[^>]+>/, ""),
    );
  }
  console.log(`Introduction website: ${output}`);
} else {
  throw new Error(
    "Use dev, build, or test; build --app integrates the local /intro/ page.",
  );
}
