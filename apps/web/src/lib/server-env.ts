import "server-only";

import path from "node:path";

import { config as loadDotenv } from "dotenv";

let loaded = false;

function ensureLoaded() {
  if (loaded) {
    return;
  }

  loadDotenv({ path: path.resolve(process.cwd(), "../../.env") });
  loaded = true;
}

export function getServerEnv(name: string) {
  ensureLoaded();
  return process.env[name];
}

export function requireServerEnv(name: string) {
  const value = getServerEnv(name);
  if (!value) {
    throw new Error(`Missing required server env var: ${name}`);
  }

  return value;
}

