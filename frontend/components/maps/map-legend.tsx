export interface MapLegendItem {
  color: string;
  label: string;
}

export function MapLegend({ items }: { items: MapLegendItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="rounded-md border bg-background/95 p-3 text-sm shadow-sm">
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.label} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-muted-foreground">{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
