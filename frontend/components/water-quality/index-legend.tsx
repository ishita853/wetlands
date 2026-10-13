import type { IndexDefinition } from "@/types/water-quality";

/**
 * Colour bar and class labels for an index, taken from the backend definition
 * (palette spread evenly from vis_min to vis_max, as in the GEE application).
 */
export function IndexLegend({ index }: { index: IndexDefinition }) {
  const gradient = `linear-gradient(to right, ${index.palette.join(", ")})`;
  const mid = (index.vis_min + index.vis_max) / 2;
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-foreground">{index.key}</p>
        <p className="text-xs text-muted-foreground">
          Display range {index.vis_min} to +{index.vis_max}
        </p>
      </div>
      <div
        className="h-3 w-full rounded-[2px] border border-border"
        style={{ backgroundImage: gradient }}
        role="img"
        aria-label={`Colour scale from ${index.vis_min} to ${index.vis_max}`}
      />
      <div className="flex justify-between text-xs tabular-nums text-muted-foreground">
        <span>{index.vis_min}</span>
        <span>{mid}</span>
        <span>+{index.vis_max}</span>
      </div>
      <ul className="space-y-1 pt-1 text-xs text-foreground/85">
        {index.legend.map((entry) => (
          <li key={entry.label} className="flex items-center gap-2">
            <span
              className="inline-block size-3 shrink-0 rounded-[2px] border border-black/10"
              style={{ backgroundColor: entry.color }}
              aria-hidden="true"
            />
            {entry.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
