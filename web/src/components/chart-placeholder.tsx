export function ChartPlaceholder({
  kicker,
  title,
}: {
  kicker: string;
  title: string;
}) {
  return (
    <figure className="flex min-w-0 flex-col gap-4">
      <figcaption className="flex flex-col gap-1">
        <span className="text-xs font-medium tracking-wide text-white/45 uppercase">
          {kicker}
        </span>
        <span className="text-lg font-semibold text-white">{title}</span>
      </figcaption>
      <div className="flex aspect-[560/300] w-full items-center justify-center rounded-lg border border-dashed border-white/15 bg-white/[0.02]">
        <span className="text-xs tracking-wide text-white/35 uppercase">
          Chart coming soon
        </span>
      </div>
    </figure>
  );
}
