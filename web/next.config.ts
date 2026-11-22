import path from "node:path";
import type { NextConfig } from "next";

// Secrets (TYPESAFE_API_KEY for the live demo) live in the repo root's .env.local.
try {
  process.loadEnvFile(path.resolve(__dirname, "../.env.local"));
} catch {
  // No root .env.local (e.g. in CI): the demo falls back to recorded scores.
}

const nextConfig: NextConfig = {
  // Note: `cacheComponents` is left off on purpose — it isn't fully supported by
  // @opennextjs/cloudflare yet (https://github.com/opennextjs/opennextjs-cloudflare/pull/1318).
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

import("@opennextjs/cloudflare").then((m) => m.initOpenNextCloudflareForDev());
