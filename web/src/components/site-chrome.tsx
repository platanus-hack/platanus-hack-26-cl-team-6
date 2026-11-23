import { FooterRays } from "./footer-rays";
import { HeroFans } from "./hero-fans";
import { LiveTranscript } from "./live-transcript";

const REPO = "https://github.com/platanus-hack/platanus-hack-26-cl-team-6";

const NAV = [
  { href: "#method", label: "Method" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-black/70 backdrop-blur-md animate-in fade-in duration-700">
      <div className="flex h-14 items-center justify-between gap-6 px-6 md:px-12 lg:px-20">
        <a
          href="#top"
          aria-label="SwarmWatch, back to top"
          className="flex items-center"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.svg"
            alt=""
            width={124}
            height={22}
            className="h-[22px] w-auto"
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
            className="flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-xs font-semibold text-black transition-colors hover:bg-white/85"
          >
            <svg
              viewBox="0 0 16 16"
              width={14}
              height={14}
              fill="currentColor"
              aria-hidden="true"
            >
              {/* Official GitHub mark (Octicons mark-github). */}
              <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
            </svg>
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
        <div className="flex flex-col items-center gap-5 animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <h1 className="max-w-xl px-12 text-4xl leading-[1.02] font-light tracking-[-0.035em] text-white md:px-0 md:text-6xl lg:text-7xl">
            Catch swarm hallucinations live, at any scale.
          </h1>
          <p className="max-w-md px-8 text-sm leading-relaxed text-white/60 md:px-0 md:text-base">
            Errors flagged before they can cascade. <br></br> Click any dot to try it live.
          </p>
        </div>
        <LiveTranscript />
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="relative mt-8 overflow-hidden border-t border-white/10 bg-black">
      <div className="relative h-[440px] md:h-[520px]">
        <FooterRays className="absolute inset-0 h-full w-full" />
        <p className="absolute bottom-10 left-6 z-10 max-w-sm text-4xl leading-[1.05] font-medium tracking-[-0.03em] text-white md:left-12 md:text-5xl lg:left-20">
          Hallucinations, caught live.
        </p>
      </div>
    </footer>
  );
}
