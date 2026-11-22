import { HeroFans } from "./hero-fans";
import { LiveTranscript } from "./live-transcript";
import { ParticleField } from "./particle-field";

const REPO = "https://github.com/platanus-hack/platanus-hack-26-cl-team-6";

const NAV = [
  { href: "#results", label: "Results" },
  { href: "#method", label: "Method" },
  { href: "#limits", label: "Limits" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-black/70 backdrop-blur-md animate-in fade-in duration-700">
      <div className="flex h-14 items-center justify-between gap-6 px-6 md:px-12 lg:px-20">
        <a
          href="#top"
          aria-label="Jev, back to top"
          className="flex items-center"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/icon.svg"
            alt=""
            width={22}
            height={22}
            className="rounded-[5px]"
          />
        </a>
        <nav className="flex items-center gap-5 text-sm text-white/60 md:gap-8">
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              className="hidden transition-colors hover:text-white sm:inline"
            >
              {n.label}
            </a>
          ))}
          <a
            href={REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-white/25 px-3.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-white hover:text-black"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}

export function Hero() {
  return (
    <section
      id="top"
      className="relative flex min-h-[calc(100svh-3.5rem)] flex-col items-center overflow-hidden bg-black px-4 pt-40 pb-20 md:pt-56"
    >
      <HeroFans />
      {/* Hairlines across the centre band, as in the reference slide. */}
      <div className="pointer-events-none absolute inset-x-0 top-[34%] h-px bg-white/[0.07]" />
      <div className="pointer-events-none absolute inset-x-0 top-[52%] h-px bg-white/[0.07]" />
      <div className="pointer-events-none absolute inset-x-0 top-[66%] h-px bg-white/[0.07]" />

      <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-col items-center gap-12 text-center md:gap-14">
        <h1 className="max-w-3xl px-12 text-4xl leading-[1.02] font-light tracking-[-0.035em] text-white animate-in fade-in slide-in-from-bottom-4 duration-1000 md:px-0 md:text-6xl lg:text-7xl">
          Can one model catch a swarm’s mistakes as they happen?
        </h1>
        <LiveTranscript />
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="relative mt-8 overflow-hidden border-t border-white/10 bg-black">
      <div className="relative h-[440px] md:h-[520px]">
        <ParticleField className="absolute inset-0 h-full w-full" />
        <p className="absolute bottom-10 left-6 z-10 max-w-sm text-4xl leading-[1.05] font-medium tracking-[-0.03em] text-white md:left-12 md:text-5xl lg:left-20">
          30 of 36 planted errors, caught live.
        </p>
      </div>
      <div className="flex flex-col gap-3 border-t border-white/10 px-6 py-6 text-xs text-white/45 md:flex-row md:items-center md:justify-between md:px-12 lg:px-20">
        <span>
          Hard set, threshold 0.85: 83% recall, 79% precision, $0.027 per 100 messages.
        </span>
        <span className="flex items-center gap-4">
          <span>Platanus Hack 26 · Team 6 · Next.js on Cloudflare Workers</span>
          <a
            href={REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="text-white/80 hover:text-white"
          >
            GitHub ↗
          </a>
        </span>
      </div>
    </footer>
  );
}
