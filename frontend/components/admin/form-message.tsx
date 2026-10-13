import { AlertCircle, CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

/** Inline status message for admin forms: icon + text, never colour alone. */
export function FormMessage({
  tone,
  title,
  items,
  children,
  className,
}: {
  tone: "error" | "success";
  title?: string;
  items?: string[];
  children?: React.ReactNode;
  className?: string;
}) {
  const Icon = tone === "error" ? AlertCircle : CheckCircle2;
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "flex gap-2.5 rounded-sm border px-3.5 py-3 text-sm",
        tone === "error"
          ? "border-destructive/40 bg-destructive/5 text-foreground"
          : "border-sedge/50 bg-accent/60 text-foreground",
        className,
      )}
    >
      <Icon
        className={cn(
          "mt-0.5 size-4 shrink-0",
          tone === "error" ? "text-destructive" : "text-sedge-strong",
        )}
        aria-hidden="true"
      />
      <div className="min-w-0">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children}
        {items?.length ? (
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
