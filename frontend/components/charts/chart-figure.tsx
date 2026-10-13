import { cn } from "@/lib/utils";

export type ChartTable = {
  columns: string[];
  rows: (string | number | null)[][];
};

/**
 * Frame for every chart: title, unit/subtitle, the chart, a data-table view
 * (so no value is conveyed by the graphic alone) and a source line.
 */
export function ChartFigure({
  title,
  subtitle,
  source,
  table,
  className,
  children,
}: {
  title: string;
  subtitle?: string;
  source?: string;
  table?: ChartTable;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <figure className={cn("min-w-0 rounded-sm border border-border bg-card", className)}>
      <figcaption className="border-b border-border px-4 py-3">
        <p className="font-semibold text-foreground">{title}</p>
        {subtitle ? <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p> : null}
      </figcaption>
      <div className="px-2 pt-2">{children}</div>
      {table || source ? (
        <div className="space-y-2 border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
          {table ? (
            <details>
              <summary className="cursor-pointer font-medium text-primary">View data table</summary>
              <div className="mt-2 max-h-72 overflow-auto">
                <table className="w-full border-collapse text-left text-xs text-foreground">
                  <thead className="sticky top-0 bg-card">
                    <tr>
                      {table.columns.map((c) => (
                        <th key={c} className="border-b border-border px-2 py-1.5 font-semibold">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, i) => (
                      <tr key={i} className="even:bg-muted/60">
                        {row.map((cell, j) => (
                          <td key={j} className="px-2 py-1 tabular-nums">
                            {cell ?? "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          ) : null}
          {source ? <p>Source: {source}</p> : null}
        </div>
      ) : null}
    </figure>
  );
}
