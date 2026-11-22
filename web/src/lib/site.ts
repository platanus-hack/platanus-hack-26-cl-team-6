export const SITE = {
  name: "SwarmWatch",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "https://platanus.ignaciopalma.com",
  title: "SwarmWatch · Hallucinations, caught live",
  tagline: "Hallucinations, caught live.",
  description:
    "SwarmWatch flags fabricated and unverified claims in multi-agent AI swarms as they are posted — 28× cheaper than a Sonnet judge, at a flat cost per message.",
  repo: "https://github.com/platanus-hack/platanus-hack-26-cl-team-6",
} as const;
