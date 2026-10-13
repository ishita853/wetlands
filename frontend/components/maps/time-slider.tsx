"use client";

export interface TimeSliderProps {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  formatLabel?: (value: number) => string;
}

/** Generic scrubber for time-based map/chart visualizations. */
export function TimeSlider({ min, max, value, onChange, formatLabel }: TimeSliderProps) {
  return (
    <div className="flex items-center gap-3 rounded-md border bg-background/95 px-3 py-2 shadow-sm">
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full"
      />
      <span className="w-24 shrink-0 text-right text-sm text-muted-foreground">
        {formatLabel ? formatLabel(value) : value}
      </span>
    </div>
  );
}
