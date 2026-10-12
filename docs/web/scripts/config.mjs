import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

export const siteRoot = fileURLToPath(new URL("..", import.meta.url));
export const appRoot = fileURLToPath(new URL("../../../web", import.meta.url));
export const appRequire = createRequire(path.join(appRoot, "package.json"));
export const dependencyAliases = Object.fromEntries(
  [
    "react",
    "react-dom",
    "gsap",
    "lucide-react",
    "vitest",
    "@testing-library/react",
  ].map((name) => [
    name,
    path.dirname(appRequire.resolve(`${name}/package.json`)),
  ]),
);
export async function loadBuildTools() {
  const vite = await import(pathToFileURL(appRequire.resolve("vite")).href);
  const react = await import(
    pathToFileURL(appRequire.resolve("@vitejs/plugin-react")).href
  );
  return { vite, react: react.default };
}
