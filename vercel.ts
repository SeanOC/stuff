// Vercel project configuration. Most concerns (function timeouts,
// runtime, framework) are already handled by Next.js auto-detection
// and per-route exports — this file mainly documents that we're on the
// modern vercel.ts stack and gives us a typed home for future routing
// rules / cron jobs.

import type { VercelConfig } from "@vercel/config/v1";

export const config: VercelConfig = {
  framework: "nextjs",
};
