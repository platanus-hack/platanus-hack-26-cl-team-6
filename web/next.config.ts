import type { NextConfig } from "next";

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
