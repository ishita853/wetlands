import { cn } from "@/lib/utils";

/** Faint contour lines, like ripples across open water. Decorative only. */
export function Waves({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={cn("pointer-events-none absolute inset-0 size-full", className)}
      viewBox="0 0 1440 480"
      preserveAspectRatio="none"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M0 64 C 240 20, 480 110, 760 76 S 1200 10, 1440 70" />
      <path d="M0 150 C 300 110, 520 190, 820 140 S 1220 90, 1440 160" />
      <path d="M0 250 C 260 210, 560 280, 860 230 S 1240 190, 1440 260" />
      <path d="M0 360 C 320 320, 600 390, 900 340 S 1260 300, 1440 370" />
    </svg>
  );
}
