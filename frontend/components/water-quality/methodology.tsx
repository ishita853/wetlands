import type { IndexDefinition } from "@/types/water-quality";

/**
 * Compact methodology summary. Formulas and bands are rendered from the
 * backend's index definitions; the text follows the project specification
 * (docs/gee-functional-specification.md).
 */
export function Methodology({ indices }: { indices: IndexDefinition[] }) {
  return (
    <section
      aria-labelledby="wq-methodology"
      className="rounded-sm border border-border border-t-4 border-t-sedge bg-card p-5"
    >
      <h2
        id="wq-methodology"
        className="text-sm font-semibold tracking-wide text-muted-foreground uppercase"
      >
        Methodology
      </h2>
      <div className="mt-3 grid gap-6 text-sm leading-relaxed text-foreground/85 lg:grid-cols-2">
        <div className="space-y-3">
          <p>
            <strong className="text-foreground">Satellite observations.</strong> Sentinel-2 MSI
            Level-2A surface reflectance, retrieved at request time from the{" "}
            <strong className="text-foreground">
              Copernicus Data Space Ecosystem through Sentinel Hub
            </strong>
            ; values are harmonized across ESA processing baselines.
          </p>
          <p>
            <strong className="text-foreground">Analysis area.</strong> Every result is computed
            only inside the wetland&apos;s boundary polygon (the ROI). The polygon defines{" "}
            <em>where</em> the analysis runs; Sentinel-2 provides the observations. Sites without a
            validated polygon are not analysed, and boundaries are never approximated from point
            coordinates.
          </p>
          <p>
            <strong className="text-foreground">Map.</strong> The Sentinel-2 acquisition with the
            lowest tile-level cloud cover in the selected period, at 10 m where the wetland size
            allows (coarser for very large sites). Cloud and cirrus pixels (Sentinel-2 scene classes
            8, 9 and 10) are masked.
          </p>
          <p>
            <strong className="text-foreground">Time series.</strong> The mean index over the
            wetland at 1000 m for every day with a Sentinel-2 acquisition in the period, without a
            cloud mask. Only actual acquisition days are plotted; Sentinel-2&apos;s nominal 5-day
            revisit does not guarantee a usable observation on any given date, and gaps are not
            filled.
          </p>
        </div>
        <div>
          <table className="w-full border-collapse text-left text-sm">
            <caption className="mb-2 text-left text-xs text-muted-foreground">
              Indices (normalized differences of Sentinel-2 bands; range −1 to +1)
            </caption>
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="py-1.5 pr-3 font-semibold">Index</th>
                <th className="py-1.5 pr-3 font-semibold">Formula</th>
              </tr>
            </thead>
            <tbody>
              {indices.map((index) => (
                <tr key={index.key} className="border-b border-border last:border-b-0">
                  <td className="py-2 pr-3 align-top">
                    <span className="font-semibold text-foreground">{index.key}</span>
                    <span className="block text-xs text-muted-foreground">{index.name}</span>
                  </td>
                  <td className="py-2 pr-3 align-top font-mono text-xs text-foreground">
                    {index.formula}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-muted-foreground">
            Bands: B03 green (10 m), B04 red (10 m), B05 red edge 1 (20 m), B08 near-infrared (10
            m), B11 short-wave infrared 1 (20 m). Each map lists its data provenance.
          </p>
        </div>
      </div>
    </section>
  );
}
