import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// No incremental cache configured yet. To enable ISR/data caching, add an R2
// bucket and use r2IncrementalCache — see https://opennext.js.org/cloudflare/caching
export default defineCloudflareConfig({});
