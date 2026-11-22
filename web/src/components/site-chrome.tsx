import { HeroFans } from "./hero-fans";
import { ParticleField } from "./particle-field";

const REPO = "https://github.com/platanus-hack/platanus-hack-26-cl-team-6";

const NAV = [
  { href: "#attack", label: "Attack" },
  { href: "#defense", label: "Defense" },
  { href: "#general", label: "General" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-black/70 backdrop-blur-md animate-in fade-in duration-700">
      <div className="flex h-14 items-center justify-between gap-6 px-6 md:px-12 lg:px-20">
        <a
          href="#top"
          className="flex items-center gap-2.5 text-sm font-semibold text-white"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/icon.svg"
            alt=""
            width={22}
            height={22}
            className="rounded-[5px]"
          />
          Swarm λ
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
      className="relative flex h-[min(78vh,820px)] min-h-[560px] items-center justify-center overflow-hidden bg-black"
    >
      <HeroFans />
      {/* Hairlines across the centre band, as in the reference slide. */}
      <div className="pointer-events-none absolute inset-x-0 top-[34%] h-px bg-white/[0.07]" />
      <div className="pointer-events-none absolute inset-x-0 top-[52%] h-px bg-white/[0.07]" />
      <div className="pointer-events-none absolute inset-x-0 top-[66%] h-px bg-white/[0.07]" />

      <div className="relative z-10 mx-auto flex max-w-3xl flex-col items-center gap-6 px-20 text-center md:px-6">
        <h1 className="text-4xl leading-[1.02] font-light tracking-[-0.035em] text-white animate-in fade-in slide-in-from-bottom-4 duration-1000 md:text-6xl lg:text-7xl">
          How far does a swarm of agents get on security work?
        </h1>
        <p className="max-w-md text-sm leading-relaxed text-white/75 animate-in fade-in slide-in-from-bottom-2 delay-300 duration-1000 fill-mode-backwards md:text-base">
          We measure Toby Ord&apos;s swarm exponent λ: N agents perform like one
          agent thinking N<sup>λ</sup> times longer. Attack on the left, defense
          on the right.
        </p>
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
          Sixteen agents, one agent thinking ~5× longer.
        </p>
      </div>
      <div className="flex flex-col gap-3 border-t border-white/10 px-6 py-6 text-xs text-white/45 md:flex-row md:items-center md:justify-between md:px-12 lg:px-20">
        <span>
          SEC-Bench Pro, λ = 0.57: 16<sup>0.57</sup> ≈ 4.8. Measured data only.
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
